"""Finite task collision geometry; does not modify the hardware protection model."""
import xml.etree.ElementTree as ET

import numpy as np


def append_boxes(root, obstacles):
    names = {link.get('name') for link in root.findall('link')}
    for item in obstacles:
        name = item['name']
        lo, hi = np.asarray(item['lo_m'], float), np.asarray(item['hi_m'], float)
        if (not name.startswith('task_obstacle_') or name in names or lo.shape != (3,)
                or hi.shape != (3,) or not np.isfinite([lo, hi]).all() or np.any(hi <= lo)):
            raise ValueError('Unique named finite obstacle bounds required')
        link = ET.SubElement(root, 'link', name=name)
        collision = ET.SubElement(link, 'collision')
        ET.SubElement(collision, 'origin', xyz=' '.join(map(str, (lo+hi)/2)))
        ET.SubElement(ET.SubElement(collision, 'geometry'), 'box', size=' '.join(map(str, hi-lo)))
        joint = ET.SubElement(root, 'joint', name=name+'_fixed', type='fixed')
        ET.SubElement(joint, 'parent', link='world')
        ET.SubElement(joint, 'child', link=name)
        names.add(name)
    return root


def static_pairs(model, root, obstacles, arms, *, objects=()):
    """Ignore only obstacle/static-cell overlap; retain every robot/object pair."""
    obstacle_names = {item['name'] for item in obstacles}
    for name in obstacle_names:
        for link in root.findall('link'):
            other = link.get('name')
            moving = other in objects or any(other.startswith(arm+'_') for arm in arms)
            if other != name and not moving:
                model.scene.allowed_collision_matrix.set_entry(name, other, True)


def robot_model(problem, obstacles, directory):
    from uwa_cell_calibration.model import CollisionModel
    root = append_boxes(ET.fromstring(problem.description), obstacles)
    model = CollisionModel(ET.tostring(root, encoding='unicode'), directory)
    for pair in ET.parse(problem.directory/'moveit/robot.srdf').findall('disable_collisions'):
        model.scene.allowed_collision_matrix.set_entry(pair.get('link1'), pair.get('link2'), True)
    static_pairs(model, root, obstacles, problem.names)
    return model
