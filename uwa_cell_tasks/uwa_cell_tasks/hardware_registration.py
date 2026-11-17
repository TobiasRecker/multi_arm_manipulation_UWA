"""Explicit coordinate binding of preliminary camera data to a revised model.

This is NOT a fresh physical extrinsic calibration. It assumes the old measured
camera/base relation still holds, and records the model-anchor correction.
The fixed-world camera profile is never overwritten or moved automatically.
"""
import xml.etree.ElementTree as ET
import numpy as np
from match_cooperative_handling.rigid_object import rigid
from uwa_cell_gazebo.charuco_views import Chain


def bind_camera_pose(description, registration, camera_object):
    camera_object=rigid(camera_object)
    old_anchor=rigid(registration['T_world_anchor_at_registration'])
    anchor_camera=rigid(registration['T_anchor_oak_optical'])
    old_camera=rigid(registration['T_world_oak_optical'])
    if not np.allclose(old_anchor@anchor_camera,old_camera,atol=1e-9,rtol=0):
        raise ValueError('Inconsistent original camera/anchor transform chain')
    anchor=registration['anchor_frame']
    if anchor!='right_front_base_link':raise ValueError('Expected the original right-front physical anchor')
    root=ET.fromstring(description)
    parents={j.find('child').get('link'):j for j in root.findall('joint')}
    link=anchor
    while link!='world':
        joint=parents.get(link)
        if joint is None or joint.get('type')!='fixed':raise ValueError('Camera binding anchor must be world-fixed in this task model')
        link=joint.find('parent').get('link')
    new_anchor=rigid(Chain(description,'world',anchor).forward({}))
    new_camera=new_anchor@anchor_camera
    return dict(T_world_object_candidate=(new_camera@camera_object).tolist(),
        T_world_camera_candidate=new_camera.tolist(),T_world_anchor_current=new_anchor.tolist(),
        T_world_anchor_original=old_anchor.tolist(),
        anchor_translation_change_m=(new_anchor[:3,3]-old_anchor[:3,3]).tolist(),
        executable=False,absolute_accuracy_validated=False,manipulation_approved=False,
        source='Existing preliminary camera/base relation re-expressed at current model anchor; not a new physical calibration',
        assumptions=['No physical camera/base displacement since preliminary relative registration',
                     'Current nominal base orientation remains provisional'],
        global_camera_profile_modified=False)
