"""Versioned session artifacts and profiles; never modify simulator geometry."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np


def atomic_json(path, data):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    temporary.replace(path)


def fingerprint(description):
    root=ET.fromstring(description)
    for element in list(root):
        if element.tag in ('gazebo','ros2_control'):root.remove(element)
    for link in root.findall('link'):
        for visual in link.findall('visual'):link.remove(visual)
    return hashlib.sha256(ET.tostring(root)).hexdigest()


def validate_result(result):
    if result.get('schema_version') != 1 or result.get('passed') is not True or not result.get('robots'):
        raise ValueError('Only successful version-1 calibration results can be activated')
    from uwa_cell_gazebo.configuration import ROBOT_IDS
    if not set(result['robots'])<=set(ROBOT_IDS):raise ValueError('Unknown robot IDs in calibration profile')
    for fit in result['robots'].values():
        if not fit['passed'] or fit['fit_count'] < 12 or fit['validation_count'] < 6:
            raise ValueError('Insufficient independent calibration/validation observations')
        total=fit['fit_count']+fit['validation_count']+len(fit.get('excluded_samples',[]))
        if not 30<=total<=50:raise ValueError('Activating a profile requires 30-50 captured distinct poses per robot')
        quality=fit['validation']
        values=np.asarray([quality[k] for k in ('median_reprojection_rms_px','board_translation_rms_m','board_rotation_rms_deg')],float)
        if not np.isfinite(values).all() or np.any(values<0):raise ValueError('Invalid quality metrics')
        if not (quality['median_reprojection_rms_px'] <= 1. and
                quality['board_translation_rms_m'] <= .005 and quality['board_rotation_rms_deg'] <= .5):
            raise ValueError('Independent validation limits exceeded')
        for key in ('T_tool0_camera','T_base_board'):
            t=np.asarray(fit[key],float)
            if t.shape != (4,4) or not np.isfinite(t).all() or not np.allclose(t[3],[0,0,0,1]) or not np.allclose(t[:3,:3].T@t[:3,:3],np.eye(3),atol=1e-5) or np.linalg.det(t[:3,:3]) < .999:
                raise ValueError(f'{key} is not a rigid transform')
        if np.linalg.norm(np.asarray(fit['T_tool0_camera'])[:3,3]) > .3:
            raise ValueError('Estimated wrist camera is more than 300 mm from tool0')
