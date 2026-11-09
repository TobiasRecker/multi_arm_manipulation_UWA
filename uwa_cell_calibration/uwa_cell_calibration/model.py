"""MoveIt collision model and separate calibrated description construction."""
import itertools
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation

from uwa_cell_gazebo.charuco import table_board_transform
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_gazebo.configuration import ROBOT_IDS


def set_origin(joint, matrix):
    origin = joint.find('origin')
    if origin is None:
        origin = ET.SubElement(joint, 'origin')
    origin.set('xyz', ' '.join(map(str, matrix[:3, 3])))
    origin.set('rpy', ' '.join(map(str, Rotation.from_matrix(matrix[:3, :3]).as_euler('xyz'))))


def calibrated_description(description, layout, result):
    root = ET.fromstring(description)
    for rid, fit in result['robots'].items():
        table = layout['robots'][rid]['table']
        table_base = table_board_transform(layout['charuco'], table) @ np.linalg.inv(fit['T_base_board'])
        mount = next(j for j in root.findall('joint') if j.find('child').get('link') == f'{rid}_base_link')
        set_origin(mount, table_base)
        local_optical = Chain(description, f'{rid}_wrist_camera_link',
                              f'{rid}_wrist_camera_optical_frame').forward({})
        set_origin(root.find(f"joint[@name='{rid}_wrist_camera_mount']"),
                   np.asarray(fit['T_tool0_camera']) @ np.linalg.inv(local_optical))
    for element in list(root):
        if element.tag in ('gazebo', 'ros2_control'):
            root.remove(element)
    for link in root.findall('link'):
        if link.get('name') != 'world':
            link.set('name', 'calibrated/'+link.get('name'))
    for element in root.findall('joint/parent') + root.findall('joint/child'):
        if element.get('link') != 'world':
            element.set('link', 'calibrated/'+element.get('link'))
    return ET.tostring(root, encoding='unicode')


def semantic_description(description):
    root = ET.fromstring(description)
    srdf = ET.Element('robot', name=root.get('name'))
    for rid in ROBOT_IDS:
        group = ET.SubElement(srdf, 'group', name=rid)
        for suffix in ('shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
                       'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint'):
            ET.SubElement(group, 'joint', name=f'{rid}_{suffix}')
    pairs = set()
    fixed = {}
    for joint in root.findall('joint'):
        a, b = joint.find('parent').get('link'), joint.find('child').get('link')
        pairs.add(tuple(sorted((a, b))))
        if joint.get('type') == 'fixed':
            fixed.setdefault(a, set()).add(b)
            fixed.setdefault(b, set()).add(a)
    anchored, todo = set(), ['world']
    while todo:
        name = todo.pop()
        if name not in anchored:
            anchored.add(name)
            todo.extend(fixed.get(name, set()) - anchored)
    pairs.update(tuple(sorted(p)) for p in itertools.combinations(anchored, 2))
    # Adjacent rigid tool members are allowed to touch. Expand only within an
    # arm, never through the world's fixed tables into another moving arm.
    for rid in ROBOT_IDS:
        prefix = 'calibrated/' if root.find(f"link[@name='calibrated/{rid}_base_link']") is not None else ''
        names = {l.get('name') for l in root.findall('link') if l.get('name').startswith(prefix+rid+'_')}
        components, seen = [], set()
        for name in names:
            if name in seen:
                continue
            todo, component = [name], set()
            while todo:
                n = todo.pop()
                if n in component:
                    continue
                component.add(n)
                todo.extend((fixed.get(n, set()) & names) - component)
            seen |= component
            components.append(component)
            pairs.update(tuple(sorted(p)) for p in itertools.combinations(component, 2))
        for joint in root.findall('joint'):
            a, b = joint.find('parent').get('link'), joint.find('child').get('link')
            if a in names and b in names:
                ca = next(c for c in components if a in c)
                cb = next(c for c in components if b in c)
                pairs.update(tuple(sorted((u,v))) for u in ca for v in cb if u != v)
        table = 'left' if rid.startswith('left') else 'right'
        pairs.add(tuple(sorted((prefix+f'{table}_table_plate', prefix+rid+'_base_link'))))
        pairs.add(tuple(sorted((prefix+f'{table}_table_plate', prefix+rid+'_base_link_inertia'))))
        # The four-bar linkage shares physical hinges absent from the URDF tree.
        for side in ('left', 'right'):
            pairs.add(tuple(sorted((prefix+rid+f'_robotiq_85_{side}_inner_knuckle_link',
                                    prefix+rid+f'_robotiq_85_{side}_finger_link'))))
            pairs.add(tuple(sorted((prefix+rid+f'_robotiq_85_{side}_inner_knuckle_link',
                                    prefix+rid+f'_robotiq_85_{side}_finger_tip_link'))))
    for a, b in sorted(pairs):
        ET.SubElement(srdf, 'disable_collisions', link1=a, link2=b, reason='Adjacent')
    return ET.tostring(srdf, encoding='unicode')


class CollisionModel:
    def __init__(self, description, directory):
        from moveit.core.robot_model import RobotModel
        from moveit.core.robot_state import RobotState
        from moveit.core.planning_scene import PlanningScene
        from moveit_msgs.msg import CollisionObject
        from shape_msgs.msg import Plane
        from geometry_msgs.msg import Pose
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        root = ET.fromstring(description)
        self.prefix = 'calibrated/' if root.find("link[@name='calibrated/left_front_base_link']") is not None else ''
        for element in list(root):
            if element.tag in ('gazebo', 'ros2_control'):
                root.remove(element)
        description = ET.tostring(root, encoding='unicode')
        (directory/'robot.urdf').write_text(description)
        (directory/'robot.srdf').write_text(semantic_description(description))
        self.description = description
        self.robot = RobotModel(str(directory/'robot.urdf'), str(directory/'robot.srdf'))
        self.state = RobotState(self.robot)
        self.scene = PlanningScene(self.robot)
        floor = CollisionObject()
        floor.header.frame_id, floor.id = 'world', 'calibration_floor'
        floor.planes = [Plane(coef=[0.,0.,1.,.003])]
        pose = Pose()
        pose.orientation.w = 1.
        floor.plane_poses = [pose]
        floor.operation = CollisionObject.ADD
        self.scene.apply_collision_object(floor)
        anchored = {'world'}
        for _ in range(len(root.findall('joint'))):
            for joint in root.findall('joint'):
                if joint.get('type') == 'fixed' and joint.find('parent').get('link') in anchored:
                    anchored.add(joint.find('child').get('link'))
        for name in anchored:
            self.scene.allowed_collision_matrix.set_entry(name, 'calibration_floor', True)
        self.bounds = {j.get('name'): (float(j.find('limit').get('lower')),
                                       float(j.find('limit').get('upper')))
                       for j in root.findall('joint') if j.get('type') == 'revolute' and j.find('mimic') is None}

    def check(self, positions, contacts=False):
        from moveit.core.collision_detection import CollisionRequest, CollisionResult
        if any(not lo-1e-8 <= positions.get(name, 0.) <= hi+1e-8 for name,(lo,hi) in self.bounds.items()):
            return False, ['joint limits']
        self.state.joint_positions = {k: float(v) for k,v in positions.items() if k in self.bounds}
        self.state.update()
        request, result = CollisionRequest(), CollisionResult()
        request.contacts, request.max_contacts = contacts, 50
        request.verbose = contacts
        self.scene.check_collision(request, result, self.state)
        # This Lyrical binding does not register collision_detection::Contact.
        return not result.collision, [f'{result.contact_count} contacts (see MoveIt log)'] if contacts else []
