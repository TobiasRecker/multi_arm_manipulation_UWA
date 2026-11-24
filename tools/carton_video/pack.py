"""Package only visual assets and stored motion references; no ROS execution."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trial', type=Path, required=True)
    p.add_argument('--run', default='run05')
    p.add_argument('--scene', default='scene05')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    run, scene = a.trial / a.run, a.trial / a.scene
    state = json.loads((run / 'state.json').read_text())
    if state['state'] != 'DONE':
        raise ValueError('Use a completed archived run.')
    assets = out / 'assets'
    assets.mkdir(exist_ok=True)
    copied = {}

    def asset(uri):
        path = Path(uri.removeprefix('file://')).resolve(strict=True)
        if path in copied:
            return copied[path]
        key = hashlib.sha256(str(path).encode()).hexdigest()[:12]
        folder = assets / key
        folder.mkdir(exist_ok=True)
        target = folder / path.name
        copied[path] = '/input/assets/' + key + '/' + path.name
        if path.suffix.lower() == '.dae':
            tree = ET.parse(path)
            if tree.getroot().tag.startswith('{'):
                ET.register_namespace('', tree.getroot().tag[1:].split('}')[0])
            # COLLADA image paths are relative to the original mesh.
            for node in tree.findall('.//{*}image/{*}init_from'):
                ref = node.text
                if ref:
                    source = Path(ref.removeprefix('file://'))
                    if not source.is_absolute():
                        source = path.parent / source
                    node.text = asset(str(source))
            tree.write(target, encoding='utf-8', xml_declaration=True)
        else:
            shutil.copyfile(path, target)
        return copied[path]

    provenance = {'kind': 'gazebo_ogre2_motion_reference_render',
                  'source_trial': str(a.trial.resolve()), 'source_run': a.run,
                  'new_contact_physics': False, 'source_hashes': {}}
    for name in ('robot.urdf', 'carton.sdf', 'world.sdf'):
        path = scene / name
        provenance['source_hashes'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        tree = ET.parse(path)
        # Never package collision meshes, controller plugins, or sensors.
        for parent in tree.iter():
            for child in list(parent):
                if child.tag in ('collision', 'plugin', 'sensor', 'ros2_control'):
                    parent.remove(child)
        for mesh in tree.findall('.//mesh'):
            if 'filename' in mesh.attrib:
                mesh.set('filename', asset(mesh.get('filename')))
            elif mesh.find('uri') is not None:
                mesh.find('uri').text = asset(mesh.findtext('uri'))
        tree.write(out / name, encoding='utf-8', xml_declaration=True)
    for name in ('plan.json', 'group.json', 'state.json'):
        shutil.copyfile(run / name, out / name)
        provenance['source_hashes'][str(run / name)] = hashlib.sha256((run / name).read_bytes()).hexdigest()
    shutil.copytree(run / 'drawing-trajectories', out / 'trajectories', dirs_exist_ok=True)
    for path in sorted((run / 'drawing-trajectories').glob('*.json')):
        provenance['source_hashes'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    provenance['assets'] = {str(k): v for k, v in copied.items()}
    (out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    for name in ('bake.py', 'encode.py', 'render_carton.cpp', 'CMakeLists.txt', 'run.bash'):
        shutil.copyfile(Path(__file__).parent / name, out / name)
    print(f'Packaged {len(copied)} visual assets in {out}')


if __name__ == '__main__':
    main()
