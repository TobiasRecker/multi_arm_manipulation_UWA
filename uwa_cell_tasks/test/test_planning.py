from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from uwa_cell_description.configuration import load_layout
from uwa_cell_tasks.core import configuration, verify
from uwa_cell_tasks.scene import prepare_scene, mass_properties
from uwa_cell_tasks.planning import grasp_candidates, actual_names


def test_contact_scene_keeps_open_geometry_mass_and_actual_fingers(tmp_path):
    layout=load_layout();cfg=configuration();record=prepare_scene(layout,cfg,tmp_path)
    verify(record)
    description=(tmp_path/'robot.urdf').read_text();root=ET.fromstring(description)
    backend=root.find("ros2_control[@name='ContactGrippers']")
    assert len(backend.findall('joint'))==12
    assert root.find("joint[@name='right_front_robotiq_85_right_knuckle_joint']/mimic") is None
    assert root.find("joint[@name='left_front_robotiq_85_right_knuckle_joint']/mimic") is not None
    assert len(actual_names(description,layout)['right_front'])==12
    com,inertia=mass_properties(record['shapes'],cfg['mass_kg'])
    assert np.linalg.eigvalsh(inertia).min()>0
    sdf=ET.fromstring((tmp_path/'carton.sdf').read_text())
    assert sdf.find('model/static').text=='false'
    assert sdf.find('model/link/inertial/mass').text=='0.3'
    # Collision prisms remain thin, not a single box/convex carton hull.
    assert len(record['shapes'])>10
    for shape in record['shapes']:
        v=np.array(shape['vertices'])
        assert np.ptp(v[:,shape['axis']])<=cfg['wall_thickness_m']+1e-8
    candidates=grasp_candidates(description,record,cfg,record['T_world_object'])
    assert len(candidates)==8
    for candidate in candidates:
        assert set(candidate['tcp_targets'])==set(cfg['arms'])
        for arm,pose in candidate['tcp_targets'].items():
            assert pose[2,3]<candidate['pregrasp'][arm][2,3]
