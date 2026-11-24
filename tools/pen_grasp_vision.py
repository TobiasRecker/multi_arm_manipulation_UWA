"""Image-only pen/adapter localization. Gemini may guide an ROI, never supply a metric pose."""
import asyncio
from base64 import b64encode
from collections import Counter
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

import cv2
import numpy as np
from scipy.spatial.transform import Rotation


class PoseRejected(ValueError):
    def __init__(self,message,candidate,overlay):
        super().__init__(message)
        self.candidate,self.overlay=candidate,overlay


def transform(value):
    value = np.asarray(value, float)
    if (value.shape != (4, 4) or not np.isfinite(value).all()
            or not np.allclose(value[3], [0, 0, 0, 1], atol=1e-9)
            or not np.allclose(value[:3,:3].T @ value[:3,:3], np.eye(3), atol=1e-6)
            or not np.isclose(np.linalg.det(value[:3,:3]), 1., atol=1e-6)):
        raise ValueError('Invalid rigid transform')
    return value


def marker_points(definition, top_turn, side_turn):
    half = definition['marker_length_m'] / 2
    square = np.array([[-half,half,0],[half,half,0],[half,-half,0],[-half,-half,0]])
    side = np.column_stack(([1,0,0],[0,0,-1],[0,1,0]))
    mount = definition['mount']
    return np.concatenate([
        square @ Rotation.from_euler('z', top_turn*90, degrees=True).as_matrix().T + mount['top_center_m'],
        square @ (side @ Rotation.from_euler('z', side_turn*90, degrees=True).as_matrix()).T + mount['side_center_m']])


def detect(image, definition, roi=None):
    if image is None or image.shape[:2] != (3040,4056):
        raise ValueError('Expected the native 4056x3040 OAK Pro image')
    x0,y0,x1,y1 = roi or (0,0,4056,3040)
    if not all(type(v) is int for v in (x0,y0,x1,y1)) or not (0<=x0<x1<=4056 and 0<=y0<y1<=3040):
        raise ValueError('Invalid native pen ROI')
    gray = cv2.cvtColor(image[y0:y1,x0:x1],cv2.COLOR_BGR2GRAY)
    parameters = cv2.aruco.DetectorParameters()
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    parameters.cornerRefinementWinSize = 3
    parameters.minMarkerPerimeterRate = .01
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco,definition['dictionary']))
    wanted = [definition['top_marker_id'], definition['side_marker_id']]
    partial = None
    # Contrast changes only thresholding; metric vertices are refined on native gray pixels.
    for name, pixels, constant, refinement in [
            ('native_edge_fit',gray,7,cv2.aruco.CORNER_REFINE_APRILTAG),
            ('native_subpixel',gray,7,cv2.aruco.CORNER_REFINE_SUBPIX),
            ('local_contrast',cv2.createCLAHE(2.,(8,8)).apply(gray),3,cv2.aruco.CORNER_REFINE_SUBPIX)]:
        parameters.adaptiveThreshConstant=constant
        parameters.cornerRefinementMethod=refinement
        parameters.adaptiveThreshWinSizeMax=63
        corners, ids, rejected = cv2.aruco.ArucoDetector(dictionary,parameters).detectMarkers(pixels)
        rows = [(int(i),c[0].copy()) for i,c in zip(ids.ravel(),corners) if i in wanted] if ids is not None else []
        counts = Counter(i for i,_ in rows)
        if any(count>1 for count in counts.values()):
            raise ValueError('Duplicate pen marker ID in the image; remove spare copies from view')
        measured={}
        for i,c in rows:
            if name=='local_contrast':
                cv2.cornerSubPix(gray,c,(2,2),(-1,-1),(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_MAX_ITER,30,.01))
            measured[i]=c+[x0,y0]
        result=measured,dict(roi=[x0,y0,x1,y1],ids=list(counts),method=name,rejected_count=len(rejected))
        if all(i in measured for i in wanted):return result
        if partial is None or len(measured)>len(partial[0]):partial=result
    return partial


def locate(image, optics, T_world_camera, definition, roi=None):
    if not definition['mount'].get('centered_confirmed'):
        raise ValueError('Confirm or measure the marker-to-adapter mounting first')
    frame = transform(T_world_camera)
    K,D = np.asarray(optics['K'],float),np.asarray(optics['D'],float)
    if (optics['device_id'] != '18443010314F3B1300' or optics['focus'] != 112
            or optics['image_size'] != [4056,3040] or K.shape!=(3,3)
            or not np.isfinite(K).all() or not np.isfinite(D).all()):
        raise ValueError('OAK Pro device, focus and native optics must match')
    corners, evidence = detect(image,definition,roi)
    order = [definition['top_marker_id'],definition['side_marker_id']]
    if not all(i in corners for i in order):
        raise ValueError('Both pen markers 97 (top) and 96 (side) are required for the initial grasp pose')
    pixels = np.concatenate([corners[i] for i in order]).astype(float)
    candidates = []
    for a,b in itertools.product(range(4),repeat=2):
        points = marker_points(definition,a,b)
        ok,rvec,tvec = cv2.solvePnP(points,pixels,K,D,flags=cv2.SOLVEPNP_SQPNP)
        if not ok:
            continue
        rvec,tvec = cv2.solvePnPRefineLM(points,pixels,K,D,rvec,tvec)
        camera = np.eye(4);camera[:3,:3]=cv2.Rodrigues(rvec)[0];camera[:3,3]=tvec.ravel()
        if np.min((points@camera[:3,:3].T+camera[:3,3])[:,2]) <= 0:
            continue
        world = frame@camera
        tilt = np.degrees(np.arccos(np.clip(world[2,2],-1,1)))
        if tilt > definition['max_upright_tilt_deg']:
            continue
        projected=cv2.projectPoints(points,rvec,tvec,K,D)[0].reshape(-1,2)
        errors=np.linalg.norm(projected-pixels,axis=1)
        rms=float(np.sqrt(np.mean(errors**2)))
        candidates.append(dict(rms=rms,max_corner=float(max(errors)),turns=[a,b],world=world,camera=camera,
                               tilt_deg=float(tilt),projected=projected))
    if not candidates:
        raise ValueError('No positive-depth upright two-marker pen pose fits the CAD mounting')
    best=min(candidates,key=lambda x:x['rms'])
    result=dict(schema_version=1,status='POSE_CANDIDATE',source='OpenCV two-plane CAD PnP',
        T_world_adapter=best['world'].tolist(),T_camera_adapter=best['camera'].tolist(),
        marker_ids=order,marker_length_m=definition['marker_length_m'],quarter_turns=best['turns'],
        reprojection_rms_px=best['rms'],max_corner_error_px=best['max_corner'],tilt_deg=best['tilt_deg'],
        corners_raw_px={str(i):corners[i].tolist() for i in order},detection=evidence,
        qualification=definition['mount']['qualification'])
    overlay=image.copy()
    for i in order:
        c=corners[i].round().astype(np.int32)
        cv2.polylines(overlay,[c],True,(0,0,255),3)
        p=c.mean(axis=0).astype(int)
        cv2.putText(overlay,f'ID {i}',tuple(p),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,0,255),2)
    if best['rms']>definition['max_reprojection_rms_px'] or best['max_corner']>definition['max_corner_error_px']:
        result.update(status='REJECTED',accepted=False)
        raise PoseRejected(f"Two-marker CAD fit rejected: RMS {best['rms']:.3f} px, worst corner {best['max_corner']:.3f} px",result,overlay)
    return result,overlay


def parse_roi(raw):
    fenced=re.fullmatch(r'```(?:json)?\s*(\{.*\})\s*```',raw.strip(),re.S|re.I)
    answer=json.loads(fenced[1] if fenced else raw)
    if not isinstance(answer,dict) or set(answer)!={'status','box_2d'}:
        raise ValueError('Unexpected Gemini pen response schema')
    if answer['status'] in ('absent','uncertain') and answer['box_2d'] is None:
        raise ValueError('Gemini reports pen '+answer['status'])
    box=answer['box_2d']
    if (answer['status']!='found' or not isinstance(box,list) or len(box)!=4
            or any(type(v) is not int or not 0<=v<=1000 for v in box)
            or not(box[0]<box[2] and box[1]<box[3])):
        raise ValueError('Invalid Gemini pen bounding box')
    y0,x0,y1,x1=box
    # Image is shown in raw sensor orientation; no implicit 180-degree mapping.
    return [max(0,int(x0*4056/1000)-60),max(0,int(y0*3040/1000)-60),
            min(4056,int(np.ceil(x1*4056/1000))+60),min(3040,int(np.ceil(y1*3040/1000))+60)]


async def gemini_roi(image, output, reason):
    from carton_hydrogen import ACP,AGY,MODEL,EFFORT,image_block
    small=cv2.resize(image,(1600,1199));ok,jpg=cv2.imencode('.jpg',small,[cv2.IMWRITE_JPEG_QUALITY,94])
    if not ok:raise ValueError('Cannot encode Gemini pen image')
    prompt=('Locate the green pen holder with the pen/rectangular gripping adapter carrying TWO ArUco labels: '
        'ID97 on top and ID96 on a perpendicular side, 30mm each. Ignore the large table boards and other tools. '
        'This is the RAW SENSOR ORIENTATION, possibly upside down. Return only JSON '
        '{"status":"found","box_2d":[top,left,bottom,right]} with coordinates normalized 0..1000, '
        'including both marker faces and the holder. If absent or uncertain use that status and null box_2d. '
        'Do not invent a metric pose, marker corners, robot targets or issue tools. Local OpenCV will remeasure. '
        'Initial local failure: '+reason)
    with TemporaryDirectory(prefix='uwa-pen-gemini-') as isolated,(output/'gemini-stderr.log').open('wb') as err:
        proc=await asyncio.create_subprocess_exec(str(AGY),'acp','--include-default-customizations=false',
            '--disable-telemetry',cwd=isolated,stdin=-1,stdout=-1,stderr=err)
        client=ACP(proc)
        try:
            async with asyncio.timeout(60):
                caps=await client.request('initialize',dict(protocolVersion=1,clientCapabilities={},clientInfo=dict(name='uwa-pen-library',version='1')))
                if not caps['agentCapabilities']['promptCapabilities'].get('image'):raise ValueError('Gemini image input unavailable')
                session=await client.request('session/new',dict(cwd=isolated,mcpServers=[]));client.session_id=session['sessionId']
                params=dict(sessionId=client.session_id)
                await client.request('session/set_config_option',{**params,'configId':'model','value':MODEL})
                selection=await client.request('session/set_config_option',{**params,'configId':'thought_level','value':EFFORT})
                selected={x['id']:x['currentValue'] for x in selection['configOptions']}
                if selected.get('model')!=MODEL or selected.get('thought_level')!=EFFORT:raise ValueError('Gemini model selection mismatch')
                result=await client.request('session/prompt',{**params,'prompt':[{'type':'text','text':prompt},image_block(jpg.tobytes())]})
                raw=''.join(client.text)
                (output/'gemini-answer.json').write_text(json.dumps(dict(raw_answer=raw,tool_activity=client.used_tools,stop_reason=result.get('stopReason')),indent=2)+'\n')
                if client.used_tools or result.get('stopReason')!='end_turn':raise ValueError('Gemini did not complete an image-only answer')
                return parse_roi(raw)
        finally:
            proc.stdin.close()
            try:await asyncio.wait_for(proc.communicate(),1)
            except TimeoutError:
                if proc.returncode is None:proc.kill()
                await proc.communicate()


def perceive(image_path, optics, frame, definition, output, *, fallback=gemini_roi):
    output.mkdir(parents=True,exist_ok=True)
    image=cv2.imread(str(image_path));attempts=[]
    def rejected(error):
        (output/'rejected-measurements.json').write_text(json.dumps(dict(attempts=attempts,error=str(error)),indent=2)+'\n')
        if isinstance(error,PoseRejected):
            (output/'rejected-pose.json').write_text(json.dumps(error.candidate,indent=2,allow_nan=False)+'\n')
            cv2.imwrite(str(output/'pen-preview.jpg'),cv2.resize(cv2.rotate(error.overlay,cv2.ROTATE_180),(1600,1199)))
    try:
        result,overlay=locate(image,optics,frame,definition)
    except ValueError as error:
        attempts.append(dict(method='opencv_full_image',error=str(error)))
        rejected(error)
        if not definition.get('gemini_fallback'):raise
        if image is None or image.shape[:2]!=(3040,4056):raise
        try:
            roi=asyncio.run(fallback(image,output,str(error)))
            result,overlay=locate(image,optics,frame,definition,roi)
        except (ValueError,RuntimeError) as second:
            attempts.append(dict(method='gemini_roi_opencv_remeasurement',error=str(second)))
            rejected(second)
            raise
        attempts.append(dict(method='gemini_roi_opencv_remeasurement',roi=roi))
    else:attempts.append(dict(method='opencv_full_image',accepted=True))
    result.update(attempts=attempts,image_sha256=hashlib.sha256(image_path.read_bytes()).hexdigest())
    (output/'object-pose.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    display=cv2.rotate(overlay,cv2.ROTATE_180)
    if not cv2.imwrite(str(output/'pen-preview.jpg'),cv2.resize(display,(1600,1199))):raise ValueError('Cannot save pen preview')
    return result
