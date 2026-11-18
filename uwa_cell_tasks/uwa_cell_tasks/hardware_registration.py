"""Explicit coordinate binding of preliminary camera data to a revised model.

This is NOT a fresh physical extrinsic calibration. It assumes the old measured
camera/base relation still holds, and records the model-anchor correction.
The fixed-world camera profile is never overwritten or moved automatically.
"""
import xml.etree.ElementTree as ET
import numpy as np
from match_cooperative_handling.rigid_object import rigid
from uwa_cell_gazebo.charuco_views import Chain


def board_camera_candidate(world_base, base_board, camera_board):
    """Static-board registration, retaining an explicit base anchor.

    All transforms map child coordinates into their named parent. This
    computes geometry only: neither a nominal world anchor nor a failed
    hand-eye fit becomes calibrated merely by composing these matrices.
    """
    return rigid(world_base) @ rigid(base_board) @ np.linalg.inv(rigid(camera_board))


def board_relative_bases(base_a_board, base_b_board):
    """T_baseA_baseB for two historical fits of the SAME fixed board."""
    return rigid(base_a_board) @ np.linalg.inv(rigid(base_b_board))


def per_arm_camera_binding(description, registration, camera_object):
    """Use the SAME observed object in each fixed, user-adopted UR base frame.

    The display world's nominal table mounts must not replace the measured
    per-base camera transforms. Keep both world representations for extra
    collision checks; they are not two physical cartons or a base recalibration.
    """
    camera_object=rigid(camera_object)
    bases={};cameras={};objects={}
    for arm in ('right_front','right_rear'):
        value=registration['transforms'][arm]
        if value['parent_frame']!=arm+'_base_link' or value['child_frame']!='oak4_rgb_optical_frame':
            raise ValueError('Unexpected per-arm camera frame convention')
        bases[arm]=rigid(Chain(description,'world',arm+'_base_link').forward({}))
        cameras[arm]=rigid(value['T_parent_child'])
        objects[arm]=bases[arm]@cameras[arm]@camera_object
    return dict(binding_kind='per_arm_camera',T_camera_object=camera_object.tolist(),
        T_world_base_by_arm={a:t.tolist() for a,t in bases.items()},
        T_base_camera_by_arm={a:t.tolist() for a,t in cameras.items()},
        world_object_by_arm={a:t.tolist() for a,t in objects.items()},
        T_world_object_candidate=objects['right_front'].tolist(),
        executable=False,absolute_accuracy_validated=False,global_camera_profile_modified=False)


def validate_per_arm_binding(description, binding):
    registration={'transforms':{a:dict(parent_frame=a+'_base_link',child_frame='oak4_rgb_optical_frame',
                  T_parent_child=t) for a,t in binding['T_base_camera_by_arm'].items()}}
    expected=per_arm_camera_binding(description,registration,binding['T_camera_object'])
    for group in ('T_world_base_by_arm','world_object_by_arm'):
        if set(binding[group])!=set(expected[group]):raise ValueError('Incomplete per-arm camera binding')
        for arm,value in expected[group].items():
            if not np.allclose(binding[group][arm],value,rtol=0,atol=1e-9):
                raise ValueError('Per-arm camera binding changed: '+group+'/'+arm)
    if not np.allclose(binding['T_world_object_candidate'],expected['T_world_object_candidate'],rtol=0,atol=1e-9):
        raise ValueError('Supplemental carton pose differs from camera binding')
    return expected['world_object_by_arm']


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
