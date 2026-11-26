#!/usr/bin/env python3
"""One current static HQ RGB-D snapshot through the existing OAK photo lease."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

WORKSPACE=Path(__file__).resolve().parents[3]


def capture(output,focus):
    source=WORKSPACE/'src/oak_camera_calibration/tools/oak4_photo_service.py'
    spec=importlib.util.spec_from_file_location('uwa_carton_depth_capture',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.PhotoCapture(WORKSPACE).capture('rgbd_hq',focus=focus)
    directory=Path(result['directory'])
    metadata=json.loads((directory/'metadata.json').read_text())
    if (not metadata.get('success') or metadata.get('kind')!='rgbd'
            or metadata.get('mode')!='rgbd_hq' or metadata.get('requested_focus')!=focus
            or metadata.get('hq',{}).get('sample_kind')!='static_rgb_stereo_hdr'):
        raise ValueError('No matching current aligned HQ RGB-D snapshot was saved')
    shutil.copytree(directory,output)
    return dict(directory=str(output.resolve()),focus=focus,mode='rgbd_hq',
                depth_frame_count=len(metadata['depth_hdr']['frames']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--focus',type=int,required=True)
    args=parser.parse_args();print(json.dumps(capture(args.output,args.focus)))
