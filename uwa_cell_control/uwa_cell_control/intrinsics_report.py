"""Archive a completed hardware intrinsic fit with original-file audit; offline."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

import cv2
import numpy as np
import yaml

from .handeye_hardware import validate_native_controls
from uwa_cell_description.calibration_profile import rigid


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit_records(session,batch):
    session=Path(session)
    expected={'sample_000':'fit',**{s['sample_id']:s['role'] for s in batch['segments']}}
    actual={p.stem:p for p in (session/'records').glob('sample_*.json')}
    if set(actual)!=set(expected):raise ValueError('Observation set is incomplete or contains unexpected IDs')
    hashes={};rows=[];pixels=set();identities=set()
    for name in sorted(expected):
        path=actual[name];record=json.loads(path.read_text())
        if (record.get('accepted') is not True or record['sample_id']!=name or
                record['role']!=expected[name] or record['robot_id']!=batch['arm']):
            raise ValueError('Rejected observation or changed identity/held-out role: '+name)
        image=(path.parent/record['image']).resolve()
        if image.parent!=path.parent.resolve():raise ValueError('Observation image must be local')
        frame=cv2.imread(str(image))
        if frame is None or [frame.shape[1],frame.shape[0]]!=record['image_size']:
            raise ValueError('Image size does not match observation')
        pixel=hashlib.sha256(frame.tobytes()).hexdigest()
        if pixel!=record['pixel_sha256'] or pixel in pixels:raise ValueError('Image changed or repeated')
        pixels.add(pixel)
        rigid(record['T_base_tool0'])
        if record.get('capture_source',{}).get('kind')=='wrist_hd_service' and not record.get('native_burst'):
            raise ValueError('Native observation has no sensor/burst provenance')
        if record.get('native_burst'):
            identities.add(record['native_burst']['camera']['uniqueCamId'])
            validate_native_controls(record['native_burst'],record['camera_settings'])
            raw=Path(record['native_burst']['directory'])/'report.json'
            hashes[str(raw)]=digest_file(raw)
        for item in (path,image):hashes[str(item.relative_to(session))]=digest_file(item)
        rows.append(record)
    if len(identities)>1:raise ValueError('Physical camera identity changed')
    return rows,hashes


def finalize(session,batch_path,output):
    session=Path(session).resolve();output=Path(output).resolve()
    batch=json.loads(Path(batch_path).read_text())
    rows,hashes=audit_records(session,batch)
    intrinsics=json.loads((session/'intrinsics.json').read_text())
    if (intrinsics.get('passed') is not True or
            intrinsics['fit_count']!=sum(r['role']=='fit' for r in rows) or
            intrinsics['validation_count']!=sum(r['role']=='validation' for r in rows)):
        raise ValueError('Intrinsic fit failed or fitting/held-out counts differ')
    output.mkdir(exist_ok=False)
    shutil.copy2(session/'intrinsics.json',output/'intrinsics.json')
    k=np.asarray(intrinsics['camera_matrix']);d=intrinsics['distortion'];width,height=intrinsics['image_size']
    info=dict(image_width=width,image_height=height,camera_name=batch['arm']+'_native_hd_focus'+str(intrinsics['focus']),
        distortion_model='plumb_bob',camera_matrix=dict(rows=3,cols=3,data=k.ravel().tolist()),
        distortion_coefficients=dict(rows=1,cols=len(d),data=d),
        rectification_matrix=dict(rows=3,cols=3,data=np.eye(3).ravel().tolist()),
        projection_matrix=dict(rows=3,cols=4,data=np.c_[k,np.zeros(3)].ravel().tolist()))
    (output/'camera_info.yaml').write_text(yaml.safe_dump(info))
    for item in (session/'session.json',Path(batch_path),session/'operator_approval.json'):
        hashes[str(item)]=digest_file(item)
    report=dict(schema=1,created_at=datetime.now().astimezone().isoformat(),passed=True,activated=False,
        arm=batch['arm'],session=str(session),count=len(rows),fit_count=intrinsics['fit_count'],
        validation_count=intrinsics['validation_count'],image_size=[width,height],focus=intrinsics['focus'],
        fit_rms_px=intrinsics['fit_rms_px'],validation_rms_px=intrinsics['validation_rms_px'],
        rms_equivalent_640_width_px=intrinsics['fit_rms_px']/(width/640),
        minimum_corners=min(r['corners'] for r in rows),source_sha256=hashes,
        quality_scope='Independent intrinsic reprojection validation, not hand-eye/base/world accuracy',
        native_controls=('Actual V4L2 focus/manual exposure checked at retained burst endpoints'
                         if all(r.get('native_burst') for r in rows) else 'Not applicable to VGA-only observations'),
        automatic_return=False,handeye_fitted=False)
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--session',type=Path,required=True);p.add_argument('--batch',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    print(json.dumps(finalize(args.session,args.batch,args.output),indent=2))


if __name__=='__main__':main()
