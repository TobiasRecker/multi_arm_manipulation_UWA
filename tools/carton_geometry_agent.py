"""Image proposal with an explicitly callable, finite local geometry evaluator.

JSON actions implement the only tool interface. ACP filesystem, terminal and
other agent tools remain disabled exactly as in the image-only client.
No robot coordinates or absolute transforms are returned to the model.
"""
import asyncio
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import numpy as np

from carton_hydrogen import ACP, AGY, MODEL, EFFORT, image_block, tabletop_preview
from carton_geometry import evaluate, model_feedback, checked_corners, overlay
from carton_hydrogen import valid_box

PROMPT = Path(__file__).resolve().parents[1]/'docs/agent_trials/PROMPT_CARTON_GEOMETRY.md'


def parse_action(raw):
    text = raw.strip()
    if text.startswith('```json') and text.endswith('```'):
        text = text[7:-3].strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError('A JSON geometry action is required')
    action = value.get('action')
    keys = {'locate_box': {'action', 'box_2d'}, 'check_geometry': {'action', 'rim_corners_2d'},
            'submit': {'action', 'measurement_id'}, 'uncertain': {'action', 'reason'}}
    if action not in keys or set(value) != keys[action]:
        raise ValueError('Only check_geometry, submit or uncertain with exact fields is allowed')
    if action == 'locate_box':
        if not valid_box(value['box_2d']):
            raise ValueError('A normalized carton bounding box is required')
    elif action == 'check_geometry':
        checked_corners(value['rim_corners_2d'])
    elif not isinstance(value[next(k for k in keys[action] if k != 'action')], str):
        raise ValueError('The action identifier/reason must be text')
    return value


async def observe(image, context, output, *, client_factory=ACP, evaluator=evaluate):
    output = Path(output)
    preview = tabletop_preview(image, native_size=context['image_size'], image_window=context['image_window'])
    jpeg = BytesIO()
    preview.save(jpeg, format='JPEG', quality=89, optimize=True)
    (output/'gemini-input.jpg').write_bytes(jpeg.getvalue())
    audit = dict(model=MODEL, effort=EFFORT, protocol='bounded_local_geometry_actions', rounds=[])
    accepted = {}
    with TemporaryDirectory(prefix='uwa-carton-geometry-') as isolated, (output/'hydrogen-stderr.log').open('wb') as stderr:
        process = await asyncio.create_subprocess_exec(str(AGY), 'acp', '--include-default-customizations=false',
            '--disable-telemetry', cwd=isolated, stdin=-1, stdout=-1, stderr=stderr)
        client = client_factory(process)
        try:
            async with asyncio.timeout(15):
                caps = await client.request('initialize', {'protocolVersion': 1, 'clientCapabilities': {},
                    'clientInfo': {'name': 'uwa-carton-geometry', 'version': '1'}})
                if not caps['agentCapabilities']['promptCapabilities'].get('image'):
                    raise ValueError('The geometry session requires image input')
                session = await client.request('session/new', {'cwd': isolated, 'mcpServers': []})
                client.session_id = session['sessionId']
                params = {'sessionId': client.session_id}
                await client.request('session/set_config_option', {**params, 'configId': 'model', 'value': MODEL})
                options = await client.request('session/set_config_option',
                    {**params, 'configId': 'thought_level', 'value': EFFORT})
                selected = {x['id']: x['currentValue'] for x in options['configOptions']}
                if selected.get('model') != MODEL or selected.get('thought_level') != EFFORT:
                    raise ValueError('Hydrogen Low was not confirmed')
            blocks = [{'type': 'text', 'text': PROMPT.read_text()}, image_block(jpeg.getvalue())]
            checks = 0
            located = False
            for number in range(1, 7):
                client.text.clear()
                started = time.monotonic()
                async with asyncio.timeout(30):
                    response = await client.request('session/prompt', {**params, 'prompt': blocks})
                raw = ''.join(client.text)
                entry = dict(round=number, raw_response=raw, duration_s=time.monotonic()-started)
                audit['rounds'].append(entry)
                # Save the RAW reply before schema validation, including malformed answers.
                (output/'hydrogen-geometry.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n')
                if response.get('stopReason') != 'end_turn' or client.used_tools:
                    raise ValueError('Only the local JSON geometry action interface may be used')
                try:
                    action = parse_action(raw)
                    entry['action'] = action
                    if action['action'] == 'uncertain':
                        raise RuntimeError('Gemini could not identify visible corner seams: '+action['reason'])
                    if action['action'] == 'submit':
                        key = action['measurement_id']
                        if key not in accepted:
                            raise ValueError('Submit must reference a successful local geometry check')
                        audit['selected_measurement_id'] = key
                        return accepted[key]
                    if action['action'] == 'locate_box':
                        if located or checks:
                            raise ValueError('The detailed image frame is frozen after the first locate_box')
                        top, left, bottom, right = action['box_2d']
                        x0,y0,x1,y1 = context['image_window']
                        w,h = x1-x0,y1-y0
                        low = np.array([x0+w*left/1000,y0+h*top/1000])
                        high = np.array([x0+w*right/1000,y0+h*bottom/1000])
                        pad = np.maximum(.15*(high-low), 40)
                        low = np.floor(np.maximum(0,low-pad)).astype(int)
                        high = np.ceil(np.minimum(context['image_size'],high+pad)).astype(int)
                        if min(high-low)<100:
                            raise ValueError('The proposed carton region is too small for corner measurement')
                        context['image_window'] = [*low.tolist(),*high.tolist()]
                        detailed = tabletop_preview(image,native_size=context['image_size'],image_window=context['image_window'])
                        stream=BytesIO();detailed.save(stream,format='JPEG',quality=92,optimize=True)
                        (output/'gemini-detail.jpg').write_bytes(stream.getvalue())
                        entry['native_detail_window']=context['image_window']
                        blocks=[{'type':'text','text':'Hier ist der native Detailausschnitt. Ab jetzt beziehen sich ALLE [y,x]-Punkte 0–1000 auf DIESES neue Bild. Markiere die vier oberen äußeren Eckfalten des ganzen Kartons und rufe check_geometry auf.'},image_block(stream.getvalue())]
                        located=True
                        continue
                    if not located:
                        raise ValueError('First locate_box, then measure on the new detailed image')
                    if checks >= 3:
                        raise RuntimeError('Three geometry calls exhausted; no pose accepted')
                    checks += 1
                    key = f'geometry-{checks}'
                    corners = action['rim_corners_2d']
                    measurement = evaluator(context, corners)
                    import cv2
                    cv2.imwrite(str(output/f'{key}-proposal.jpg'),overlay(image,context,corners,measurement))
                    entry.update(measurement_id=key, geometry=model_feedback(context, measurement))
                    if measurement['success']:
                        accepted[key] = dict(corners=corners, result=measurement, measurement_id=key)
                    blocks = [{'type': 'text', 'text': json.dumps(dict(
                        tool='check_geometry', measurement_id=key, **entry['geometry']), ensure_ascii=False)
                        +'\nPrüfe die Punkte am ursprünglichen Foto. Submit nur nach bestandener Prüfung.'}]
                except (ValueError, TypeError, KeyError) as error:
                    entry['validation_error'] = str(error)
                    blocks = [{'type': 'text', 'text': 'Aktion verworfen: '+str(error)+
                        '. Korrigiere anhand des ursprünglichen Fotos. Keine Pose wurde übernommen.'}]
            raise RuntimeError('No checked geometry proposal submitted within the bounded session')
        finally:
            (output/'hydrogen-geometry.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n')
            process.stdin.close()
            try:
                await asyncio.wait_for(process.communicate(), 1)
            except TimeoutError:
                if process.returncode is None:
                    process.kill()
                await process.communicate()
