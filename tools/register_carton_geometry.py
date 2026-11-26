#!/usr/bin/env python3
"""Current native photo -> mesh landmark pose. Pure task measurement, no motion."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'uwa_cell_tasks'))
from carton_camera_session import validate_session
from carton_geometry import mesh_landmarks, evaluate, overlay
from carton_geometry_agent import observe, PROMPT

ASSET = REPO/'uwa_cell_description/assets/carton_avocado_v1/asset.json'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def context_for(image, metadata, intrinsics, session_path, description):
    from uwa_cell_gazebo.charuco_views import Chain
    photo = read(metadata)
    session = validate_session(read(session_path), intrinsics, photo=photo)
    optics = session['optics']
    pixels = cv2.imread(str(image))
    if (pixels is None or list(pixels.shape[1::-1]) != optics['image_size']
            or photo.get('success') is not True or photo.get('mode') != 'standard'):
        raise ValueError('A current native Standard photo matching the camera session is required')
    model = Path(description).read_text()
    Twb = Chain(model, 'world', 'right_charuco').forward({})
    Twt = Chain(model, 'world', 'right_table_top').forward({})
    Twc = Twb @ np.linalg.inv(np.asarray(session['T_camera_board']))
    size = optics['image_size']
    window = (775, 1750, 5350, 5260) if size == [8000, 6000] else (0, 0, *size)
    return dict(K=optics['K'], D=optics['D'], image_size=size, image_window=list(window),
                T_camera_table=(np.linalg.inv(Twc) @ Twt).tolist(), T_world_table=Twt.tolist(),
                T_camera_board=session['T_camera_board'],
                model_corners_m=mesh_landmarks(ASSET).tolist(), device_id=optics['device_id'],
                focus=optics['focus'], floor_z_m=read(ASSET)['quality']['wall_thickness_m'])


def register(args):
    from uwa_cell_tasks.hardware_registration import per_arm_camera_binding, validate_per_arm_binding
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    context = context_for(args.image, args.metadata, args.intrinsics, args.camera_session, args.description)
    write(output/'geometry-context.json', context)
    report = dict(success=False, method='direct_mesh_landmarks', attempts=[], device_commands=[],
                  support_prior='Existing carton mesh upright on fixed table; current image landmarks')
    try:
        if args.landmarks:
            observation=read(args.landmarks)
            for field,path in [('image_sha256',args.image),('metadata_sha256',args.metadata)]:
                if observation.get(field)!=hashlib.sha256(path.read_bytes()).hexdigest():
                    raise ValueError('Recorded landmarks do not belong to this exact image/metadata')
            x0,y0,x1,y1=observation['image_window'];width,height=context['image_size']
            if not (0<=x0<x1<=width and 0<=y0<y1<=height):
                raise ValueError('Recorded detail window lies outside the native image')
            context['image_window']=observation['image_window']
            corners = observation['rim_corners_2d']
            selected = dict(corners=corners, result=evaluate(context, corners), measurement_id='recorded-landmarks')
        else:
            selected = asyncio.run(observe(args.image, context, output))
        # The agent may request one native detail crop before any measurement.
        write(output/'geometry-context.json', context)
        result, corners = selected['result'], selected['corners']
        write(output/'geometry-result.json', selected)
        cv2.imwrite(str(output/'landmark-preview.jpg'), overlay(args.image, context, corners, result))
        report.update(geometry=result, landmark_preview=str(output/'landmark-preview.jpg'))
        if not result['success']:
            raise ValueError(result['error'])
        Tct = np.asarray(context['T_camera_table'])
        Tco = Tct @ np.asarray(result['T_table_object'])
        Twt = np.asarray(context['T_world_table'])
        Twc = Twt @ np.linalg.inv(Tct)
        description = args.description.read_text()
        from uwa_cell_gazebo.charuco_views import Chain
        registration = dict(transforms={arm: dict(parent_frame=arm+'_base_link',
            child_frame='oak4_rgb_optical_frame', T_parent_child=(np.linalg.inv(
                Chain(description, 'world', arm+'_base_link').forward({})) @ Twc).tolist())
            for arm in ['right_front', 'right_rear']})
        binding = per_arm_camera_binding(description, registration, Tco)
        import carton_geometry, carton_geometry_agent
        sources = [args.image, args.metadata, args.intrinsics, args.camera_session, args.description,
                   ASSET, ASSET.parent/read(ASSET)['visual_mesh'], Path(__file__),
                   Path(carton_geometry.__file__), Path(carton_geometry_agent.__file__), PROMPT,
                   output/'geometry-context.json', output/'geometry-result.json']
        if args.rgbd_directory:
            import carton_depth_geometry
            try:
                depth=carton_depth_geometry.check_depth(args.rgbd_directory,context,result,args.metadata)
            except (ValueError,KeyError,TypeError,OSError) as error:
                depth=dict(status='unavailable',reason=str(error),depth_used_for_pose=False)
            write(output/'depth-geometry.json',depth)
            report['depth_geometry']=depth
            sources += [Path(carton_depth_geometry.__file__),output/'depth-geometry.json',
                        args.rgbd_directory/'metadata.json',*map(Path,depth.get('sources',[]))]
        if args.landmarks:
            sources.append(args.landmarks)
        elif (output/'hydrogen-geometry.json').is_file():
            sources.append(output/'hydrogen-geometry.json')
        binding.update(source='Current mesh corner measurement + calibrated camera + fixed table',
                       focus=context['focus'], support_prior=report['support_prior'],
                       source_inputs={str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
        validate_per_arm_binding(description, binding)
        write(output/'object-pose.json', binding)
        report.update(success=True, object_pose=str(output/'object-pose.json'),
                      T_world_object=(Twt @ np.asarray(result['T_table_object'])).tolist(),
                      absolute_accuracy_validated=False, preview=str(output/'landmark-preview.jpg'))
        # Existing library preview consumer, with actual connected raster marks.
        cv2.imwrite(str(output/'pose-preview.jpg'), overlay(args.image, context, corners, result))
    except (ValueError, KeyError, TypeError, RuntimeError, OSError, TimeoutError) as error:
        report['error'] = str(error)
    write(output/'geometry-context.json', context)
    write(output/'registration.json', report)
    print(json.dumps(report, ensure_ascii=False, allow_nan=False))
    return 0 if report['success'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['image', 'metadata', 'intrinsics', 'camera-session', 'description', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--landmarks', type=Path, help='Explicit recorded proposal; still evaluated from current pixels')
    parser.add_argument('--rgbd-directory',type=Path,help='Optional aligned RGB-D snapshot; checked separately from native pixels')
    raise SystemExit(register(parser.parse_args()))
