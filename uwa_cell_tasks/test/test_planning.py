from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pytest
from uwa_cell_description.configuration import load_layout
from uwa_cell_tasks.core import configuration, verify
from uwa_cell_tasks.scene import prepare_scene, mass_properties,verify_scene
from uwa_cell_tasks.planning import grasp_candidates, actual_names


def test_contact_scene_keeps_open_geometry_mass_and_actual_fingers(tmp_path):
    layout=load_layout();cfg=configuration();cfg.update(physics_step_s=.0005,
        exploration_mode=True,gripper_motor_torque_limit_nm=.7,
        joint_velocity_overrides_rad_s={'right_front_wrist_1_joint':.065})
    record=prepare_scene(layout,cfg,tmp_path)
    verify(record)
    com,_=mass_properties(record['shapes'],cfg['mass_kg'])
    assert np.allclose(record['lift_reference_point_object_m'],com)
    assert any(path.endswith('/rigid_object.py') for path in record['implementation_sha256'])
    assert any(path.endswith('/runtime.py') for path in record['implementation_sha256'])
    assert any(path.endswith('/geometry.py') for path in record['implementation_sha256'])
    assert any(path.endswith('/trajectory.py') for path in record['implementation_sha256'])
    description=(tmp_path/'robot.urdf').read_text();root=ET.fromstring(description)
    backend=root.find("ros2_control[@name='ContactGrippers']")
    assert len(backend.findall('joint'))==12
    assert float(backend.find("hardware/param[@name='motor_max_torque']").text)==.7
    assert float(backend.find("hardware/param[@name='max_torque']").text)==.35
    arms=root.find("ros2_control[@name='ContactArms']")
    assert float(arms.find("hardware/param[@name='max_velocity']").text)==.065
    assert len(arms.findall('joint'))==12
    assert all([c.get('name') for c in j.findall('command_interface')]==['position','velocity'] for j in arms.findall('joint'))
    assert not any(j.get('name').startswith(('right_front_','right_rear_'))
        for j in root.find("ros2_control[@name='UwaCellSystem']").findall('joint'))
    assert root.find("joint[@name='right_front_robotiq_85_right_knuckle_joint']/mimic") is None
    assert float(root.find("joint[@name='right_front_robotiq_85_right_knuckle_joint']/dynamics").get('damping'))==cfg['finger_joint_damping_nm_s']
    assert root.find("joint[@name='left_front_robotiq_85_right_knuckle_joint']/mimic") is not None
    from uwa_cell_tasks.scene import physics_description
    # Exercise the optional native profile even when the default is the
    # experimental elastic comparison mode.
    native_description=ET.fromstring(description)
    native_description.find("ros2_control[@name='ContactGrippers']/hardware/param[@name='native_mimic']").text='true'
    physical=ET.fromstring(physics_description(ET.tostring(native_description,encoding='unicode')))
    assert physical.find("joint[@name='right_front_robotiq_85_right_knuckle_joint']/mimic").get('multiplier')=='-1'
    assert physical.find("joint[@name='left_front_robotiq_85_right_knuckle_joint']/mimic") is None
    # No passive controller interface or physics reset is introduced. Native
    # constraints are absent from the measured-state planning/TF description.
    assert len([j for j in backend.findall('joint') if j.findall('command_interface')])==2
    assert not physical.findall('.//plugin/pose')
    assert [j.get('name') for j in physical.findall('joint') if j.find('parent').get('link')=='world']==['world_to_task_cell_anchor']
    from uwa_cell_gazebo.charuco_views import Chain
    state={j.get('name'):.1 for j in root.findall('joint') if j.get('type')=='revolute'}
    for arm in layout['robots']:
        frame=arm+'_tool0'
        assert np.allclose(Chain(description,'world',frame).forward(state),
            Chain(ET.tostring(physical,encoding='unicode'),'world',frame).forward(state),atol=1e-12)
    assert len(actual_names(description,layout)['right_front'])==12
    # Both analytic volumes conservatively cover the source triangle surface;
    # the inner contact plane remains at the original mesh extremum.
    from urllib.parse import urlparse,unquote
    dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
    for model in record['fingertip_collision_models']:
        data=Path(unquote(urlparse(model['source_mesh']).path)).read_bytes()
        triangles=np.frombuffer(data[84:],dtype=dtype)['vertices'].astype(float)
        points=np.vstack([triangles.reshape(-1,3),triangles.mean(axis=1)])
        b,p=np.array(model['housing_bounds']),np.array(model['pad_bounds'])
        contained=lambda limits:np.all((points>=limits[0]-1e-9)&(points<=limits[1]+1e-9),axis=1)
        assert np.all(contained(b)|contained(p))
        sign=model['inner_plane_direction']
        assert (p[:,0]*sign).max()==pytest.approx((points[:,0]*sign).max())
        assert root.find(f"link[@name='{model['pad_link']}']/collision/geometry/box") is not None
    com,inertia=mass_properties(record['shapes'],cfg['mass_kg'])
    assert np.linalg.eigvalsh(inertia).min()>0
    sdf=ET.fromstring((tmp_path/'carton.sdf').read_text())
    assert sdf.find('model/static').text=='false'
    assert cfg['mass_kg']==.5  # User-reported carton mass,2026-11-16.
    assert float(sdf.find('model/link/inertial/mass').text)==cfg['mass_kg']
    assert record['force_backend_sha256']
    assert float(ET.parse(tmp_path/'world.sdf').getroot().find('world/physics/max_step_size').text)==.0005
    assert ET.parse(tmp_path/'world.sdf').getroot().find("world/plugin[@name='uwa_cell_tasks::ForceTelemetry']") is not None
    # Main wall contact patches are single analytic boxes; cutouts stay in
    # separate exact prisms above them instead of a seam through the pinch.
    assert len(sdf.findall('model/link/collision/geometry/box'))>=4
    assert all(shape['wall_base_top_m']>.12 for shape in record['shapes'] if shape['axis']!=2)
    # Collision prisms remain thin, not a single box/convex carton hull.
    assert len(record['shapes'])>10
    for shape in record['shapes']:
        v=np.array(shape['vertices'])
        assert np.ptp(v[:,shape['axis']])<=cfg['wall_thickness_m']+1e-8
    candidates=grasp_candidates(description,record,cfg,record['T_world_object'])
    assert len(candidates)==10
    from scipy.spatial.transform import Rotation
    tilted=np.array(record['T_world_object']);tilted[:3,:3]=tilted[:3,:3]@Rotation.from_euler('x',.01).as_matrix()
    upright=grasp_candidates(description,record,cfg,tilted)
    for candidate in upright:
        for arm in cfg['arms']:
            tool_base=Chain(description,arm+'_tool0',arm+'_robotiq_85_base_link').forward({})
            base=np.array(candidate['tcp_targets'][arm])@tool_base
            assert np.allclose(base[:3,2],[0,0,-1],atol=1e-12)
    tilted[:3,:3]=Rotation.from_euler('x',.1).as_matrix()
    with pytest.raises(ValueError,match='upright carton'):grasp_candidates(description,record,cfg,tilted)
    for candidate in candidates:
        assert set(candidate['tcp_targets'])==set(cfg['arms'])
        assert sum(candidate['estimated_vertical_load_n'].values())==pytest.approx(cfg['mass_kg']*9.81)
        assert .05<candidate['gravity_projection_fraction']<.95
        for arm,pose in candidate['tcp_targets'].items():
            assert pose[2,3]<candidate['pregrasp'][arm][2,3]
            assert .04<candidate['contacts'][arm]['point_object'][2]<.17
            contact=candidate['contacts'][arm]
            assert contact['nominal_pad_top_object_m']<=contact['continuous_wall_top_object_m']-.003+1e-10
    verify_scene(tmp_path)
    from uwa_cell_calibration.model import CollisionModel
    from uwa_cell_tasks.scene import inherit_pad_adjacency
    model=CollisionModel(description,tmp_path/'fcl')
    inherit_pad_adjacency(model)
    initial={j:0. for j in model.bounds}
    from uwa_cell_description.configuration import joint_names
    for arm,robot in layout['robots'].items():initial.update(zip(joint_names(arm),robot['initial_positions']))
    assert model.check(initial)[0]
    from uwa_cell_tasks.planning import TaskProblem
    problem=TaskProblem(tmp_path/'native-parity',description,layout,record,record['T_world_object'])
    srdf=ET.parse(tmp_path/'native-parity/moveit/robot.srdf').getroot()
    pairs={frozenset((e.get('link1'),e.get('link2'))) for e in srdf.findall('disable_collisions')}
    for arm in cfg['arms']:
        for side in ('left','right'):
            assert frozenset((arm+'_robotiq_85_'+side+'_finger_tip_pad_link',
                arm+'_robotiq_85_'+side+'_inner_knuckle_link')) in pairs
    # Cross-process check: a zero-length path valid in Python must also be
    # accepted by the installed native RRT worker with the persisted SRDF.
    names=[j for arm in cfg['arms'] for j in joint_names(arm)]
    request=dict(start=initial,joint_names=names,target=[initial[j] for j in names])
    assert problem.check(request,request['target'])
    path,error=problem.rrt(request,0,2.)
    assert path is not None,error
    (tmp_path/'robot.urdf').write_text(description+'<!-- changed -->')
    with pytest.raises(ValueError,match='robot description changed'):verify_scene(tmp_path)


def test_wall_decomposition_preserves_steps_and_rejects_internal_holes():
    from uwa_cell_tasks.scene import wall_strips
    from scipy.spatial import ConvexHull
    def polygon(points):return np.array([[0.,x,z] for x,z in points])
    # A vertical notch step must keep its two one-sided heights.
    source=[polygon([(0,0),(1,0),(1,2),(0,2)]),polygon([(1,0),(2,0),(2,1),(1,1)])]
    strips,top=wall_strips(source,0)
    assert top==pytest.approx(1.)
    assert sum(ConvexHull(p[:,[1,2]]).volume for p in strips)==pytest.approx(3.)
    hole=[polygon([(0,0),(3,0),(3,1),(0,1)]),polygon([(0,2),(3,2),(3,3),(0,3)]),
          polygon([(0,1),(1,1),(1,2),(0,2)]),polygon([(2,1),(3,1),(3,2),(2,2)])]
    with pytest.raises(ValueError,match='holes/overlaps'):wall_strips(hole,0)


def test_support_collision_permission_is_shallow_and_object_only():
    from types import SimpleNamespace
    from uwa_cell_tasks.planning import support_exemptions
    entries={}
    matrix=SimpleNamespace(set_entry=lambda a,b,value:entries.update({(a,b):value}))
    problem=SimpleNamespace(scene_record=dict(object_id='carton',shapes=[dict(vertices=[[0,0,0],[.1,.1,.2]])]),
        layout=dict(tables=dict(right=dict(xyz=[0,0,0],rpy=[0,0,0],height=.9))),
        collision=SimpleNamespace(scene=SimpleNamespace(allowed_collision_matrix=matrix)))
    for z,allowed in [(.9,True),(.9005,True),(.8995,True),(.898,False),(.902,False)]:
        pose=np.eye(4);pose[2,3]=z;support_exemptions(problem,pose)
        assert entries=={('right_table_plate','carton'):allowed}


def test_snapshot_renderer_has_no_commands_and_preserves_measured_fk(tmp_path):
    from uwa_cell_tasks.snapshot_camera import frozen_robot
    from uwa_cell_gazebo.charuco_views import Chain
    layout=load_layout();cfg=configuration();prepare_scene(layout,cfg,tmp_path)
    original=(tmp_path/'robot.urdf').read_text();root=ET.fromstring(original)
    state={j.get('name'):.1 for j in root.findall('joint') if j.get('type')=='revolute'}
    state['right_front_robotiq_85_left_knuckle_joint']=.45
    state['right_front_robotiq_85_left_finger_tip_joint']=-.3
    frozen=frozen_robot(original,state,'/uwa_grasp_test/photo');snapshot=ET.fromstring(frozen)
    assert not snapshot.findall('ros2_control')
    assert not snapshot.findall('.//plugin') and not snapshot.findall('link/collision')
    assert all(j.get('type')=='fixed' for j in snapshot.findall('joint'))
    for frame in ('right_front_tool0','right_front_robotiq_85_left_finger_tip_link','right_rear_wrist_camera_optical_frame'):
        assert np.allclose(Chain(original,'world',frame).forward(state),Chain(frozen,'world',frame).forward({}),atol=1e-10)


def test_quarter_turn_clearance_pivot_and_sideways_support():
    from uwa_cell_tasks.planning import carton_motion_poses,object_pose_at
    from itertools import product
    # Full corners conservatively represent the carton envelope. Origin at a
    # corner deliberately detects rotation around the wrong asset point.
    vertices=np.array(list(product([0.,.4],[0.,.34],[0.,.16])))
    camera=np.eye(4);camera[:3,3]=[1.2,.05,1.85]
    scene=dict(shapes=[dict(vertices=vertices)],lift_reference_point_object_m=[.2,.17,.05],T_world_overview_optical=camera)
    layout=load_layout();obj=np.eye(4);obj[:3,3]=[.06,-.2,.9]
    cfg=dict(lift_m=.03,roll_long_axis=True,rotation_clearance_m=.02,maximum_roll_lift_m=.25)
    poses=carton_motion_poses(scene,layout,obj,cfg)
    assert poses['axis_object']==0 and abs(poses['angle_rad'])==pytest.approx(np.pi/2)
    assert poses['lift_m']>.03 and poses['opening_camera_cosine']>0
    pivot=np.array(poses['pivot'])
    centre=poses['lifted'][:3,:3]@pivot+poses['lifted'][:3,3]
    for u in np.linspace(0,1,1001):
        pose=object_pose_at(poses['lifted'],poses['turned'],u,pivot)
        assert np.allclose(pose[:3,:3]@pivot+pose[:3,3],centre)
        assert (vertices@pose[:3,:3].T+pose[:3,3])[:,2].min()>=.92
    world=vertices@poses['placed'][:3,:3].T+poses['placed'][:3,3]
    assert world[:,2].min()==pytest.approx(.9)
    table=layout['tables'][poses['support_table']]
    assert np.max(abs(world[:,0]-table['xyz'][0]))<=table['width']/2-.005+1e-12
    assert np.max(abs(world[:,1]-table['xyz'][1]))<=table['length']/2-.005+1e-12
    cfg['maximum_roll_lift_m']=.04
    with pytest.raises(ValueError,match='lift envelope'):carton_motion_poses(scene,layout,obj,cfg)
    legacy=carton_motion_poses(scene,layout,obj,dict(lift_m=.03))
    assert 'turned' not in legacy and legacy['pivot'] is None
    assert np.allclose(legacy['placed'],obj)
