from pathlib import Path
from types import SimpleNamespace as NS
import json
import sys
import tempfile
import struct
import xml.etree.ElementTree as ET
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.hardware_state import DeviceStates,Peer,require_domain,MotionOutputReader
from uwa_cell_motion.hardware_ports import unsafe_controllers,hold_owned,matching_hardware,HOLD
from uwa_cell_motion.hardware_model import HardwareProblem,inventory_path
from uwa_cell_motion.common import config,nominal_state,joint_names


def test_runtime_domains_do_not_cross_simulation_or_hardware(monkeypatch):
    monkeypatch.setenv('ROS_AUTOMATIC_DISCOVERY_RANGE','LOCALHOST')
    for domain,mode,allowed in [('64','hardware',False),('66','mock',False),('67','hardware',False),('66','hardware',True),('67','mock',True)]:
        monkeypatch.setenv('ROS_DOMAIN_ID',domain)
        if allowed:require_domain(mode)
        else:
            with pytest.raises(RuntimeError):require_domain(mode)


def test_frozen_device_timestamp_does_not_refresh_even_if_ros_or_receipts_advance():
    state=DeviceStates();assert state.accept('arm',10,[0]*6,[0]*6,100)
    assert not state.accept('arm',10,[0]*6,[0]*6,100.5)
    records,errors=state.snapshot();assert records['arm']['received']==100 and 'FROZEN' in errors['arm']
    assert state.accept('arm',10.1,[0]*6,[0]*6,100.6)
    assert abs(state.snapshot()[0]['arm']['source_stamp']-100.1)<1e-8


def test_device_epoch_is_detectable_and_recovers_data_without_releasing_latches():
    state=DeviceStates();state.accept('arm',50,[0]*6,[0]*6,100)
    state.accept('arm',1,[0]*6,[0]*6,101);record=state.snapshot()[0]['arm'];assert record['epoch']==1
    assert record['source_stamp']==101
    assert not state.accept('arm',2,[float('nan')]*6,[0]*6,102)


def test_peer_replay_transport_age_and_mode_mismatch_are_rejected():
    peer=Peer();value=dict(hardware_signature='s',armed=True,sequence=1,instance='a',evaluated_monotonic_s=1.)
    assert peer.receive(value,1.01,'s',True);assert peer.fresh(1.1,.2)
    assert not peer.receive(value,1.15,'s',True)
    assert not peer.receive(dict(value,sequence=2),1.15,'s',False)
    assert not peer.fresh(1.3,.2)


def test_connection_waits_for_fresh_packets_without_activating_or_relaxing_runtime_health():
    from uwa_cell_motion.hardware_execution import HardwareClient
    calls=[]
    def health():
        calls.append('health')
        if calls.count('health')<3:raise RuntimeError('HARDWARE STATE STALE')
    client=NS(positions={'q':0.},names={'r':['q']},guard={},supervisor={},selected=['r'],driver={'r':{}},
              wait=lambda predicate,timeout:predicate(),health=health,
              spin_once=lambda **kwargs:calls.append('spin'))
    HardwareClient.connect(client)
    assert calls==['health','spin','health','spin','health']


def test_rtde_codec_reads_native_program_and_safety_without_input_recipes():
    reader=object.__new__(MotionOutputReader);reader.recipe=3
    payload=b'\x03'+struct.pack('>13dIii',12.,*([.1]*6),*([.2]*6),2,7,1)
    reader.receive=lambda:(85,payload)
    stamp,q,v,status=reader.sample();assert stamp==12. and q==[.1]*6 and v==[.2]*6
    assert status==dict(runtime_state=2,robot_mode=7,safety_mode=1)


def test_rtde_subscription_negotiation_does_not_relax_runtime_state_timeout(monkeypatch):
    from uwa_cell_motion import hardware_state
    timeouts=[]
    class Socket:
        def settimeout(self,value):timeouts.append(value)
        def close(self):pass
    monkeypatch.setattr(hardware_state.socket,'create_connection',lambda *a,**k:Socket())
    def request(self,kind,payload=b''):
        return b'\x01DOUBLE,VECTOR6D,VECTOR6D,UINT32,INT32,INT32' if kind==79 else b'\x01'
    monkeypatch.setattr(MotionOutputReader,'request',request)
    reader=MotionOutputReader('fake');assert timeouts==[2.,.2];reader.close()


def test_resource_blocker_covers_unknown_joint_owner_and_native_modes_not_gripper():
    def controller(name,claimed=(),state='active',kind='test'):return NS(name=name,state=state,type=kind,claimed_interfaces=claimed)
    joints=['q'+str(i) for i in range(6)]
    controllers=[controller('custom',[joints[0]+'/velocity']),controller('freedrive_mode_controller'),
                 controller('gripper',['finger/position']),controller(HOLD,[j+'/position' for j in joints],kind='uwa_cell_motion/CollisionHold')]
    assert set(unsafe_controllers(controllers,joints))=={'custom','freedrive_mode_controller'}
    assert hold_owned(controllers,joints)
    components=[NS(plugin_name='ur_robot_driver/URPositionHardwareInterface',command_interfaces=[NS(name=j+'/position') for j in joints])]
    assert matching_hardware(components,joints,'hardware') and not matching_hardware(components,joints,'mock')


@pytest.fixture(scope='module')
def problem():
    with tempfile.TemporaryDirectory() as directory:
        yield HardwareProblem(directory,config(Path(__file__).parents[1]/'config/hardware_motion.yaml'),inventory_path())


def test_hardware_envelope_is_valid_at_nominal_and_internal_exemptions_are_scoped(problem):
    assert problem.collision.check(nominal_state(problem.layout))[0]
    srdf=ET.parse(problem.directory/'moveit/robot.srdf')
    pairs=[p for p in srdf.findall('disable_collisions') if p.get('reason')=='CoupledToolOpeningEnvelope']
    assert pairs and all(p.get('link1').split('_robotiq_')[0]==p.get('link2').split('_robotiq_')[0] and '_robotiq_' in p.get('link1') and '_robotiq_' in p.get('link2') for p in pairs)


def test_slow_commissioning_reduces_motion_bound_without_relaxing_other_reserves(problem):
    from uwa_cell_gazebo.charuco_views import Chain
    root=Path(__file__).parents[1]/'config'
    regular=config(root/'hardware_motion.yaml');slow=config(root/'hardware_commissioning.yaml')
    assert {k for k in slow if slow[k]!=regular[k]}=={'velocity_limit_rad_s','acceleration_limit_rad_s2'}
    assert slow['velocity_limit_rad_s']<regular['velocity_limit_rad_s']
    assert slow['acceleration_limit_rad_s2']<regular['acceleration_limit_rad_s2']
    for rid,names in problem.names.items():
        v=np.zeros(len(names))
        assert problem.spheres.arm_budget(rid,v,.2,slow)[0]<problem.spheres.arm_budget(rid,v,.2,regular)[0]
    bases=[Chain(problem.description,'world',rid+'_base_link').forward({})[:3,3]
           for rid in ('left_rear','right_rear')]
    assert np.linalg.norm(bases[1]-bases[0])==pytest.approx(.991)


def test_tool_envelope_covers_full_body_volume_at_between_sample_openings(problem):
    from uwa_cell_control.scan_separation import Geometry
    geometry=Geometry(problem.original_description,problem.names);root=ET.fromstring(problem.description)
    zero={j:0. for n in problem.names.values() for j in n};frames0=geometry.fk.frames(zero);rng=np.random.default_rng(15)
    for rid,bodies in geometry.bodies.items():
        for body in bodies:
            if body.radii[-1]<=0:continue
            collisions=root.find(f"link[@name='{body.link}']").findall('collision')
            centres=np.array([np.fromstring(c.find('origin').get('xyz'),sep=' ') for c in collisions]);radii=np.array([float(c.find('geometry/sphere').get('radius')) for c in collisions])
            local=rng.uniform(body.visual_vertices.min(axis=0),body.visual_vertices.max(axis=0),size=(20,3));local=local@body.fixed[:3,:3].T+body.fixed[:3,3]
            for opening in (.0,.049,.157,.351,.793,.8):
                frames=geometry.fk.frames(dict(zero,**{problem.names[rid][6]:opening}));T=np.linalg.inv(frames0[body.link])@frames[body.link]
                points=local@T[:3,:3].T+T[:3,3]
                assert np.all(np.min(np.linalg.norm(points[:,None]-centres[None],axis=2)-radii[None],axis=1)<=1e-9)


@pytest.mark.parametrize('method',['rrtconnect','circular'])
def test_both_hardware_planners_share_tool_envelope_and_bound_results(problem,method):
    start=nominal_state(problem.layout);target=[start[j] for j in joint_names('right_rear')];target[-1]+=.01
    result=problem.plan(dict(start=start,goals={'right_rear':target}),method)
    assert result['success'] and result['hardware_plan'] and not result['simulation_only']
    assert result['hardware_binding']==problem.binding
    assert result['metrics']['full_cell_collision_checked']
    bad=dict(start);bad[problem.names['right_rear'][6]]=.2
    with pytest.raises(ValueError,match='model coordinates'):problem.normalize(dict(start=bad,goals={'right_rear':target}))


def test_native_rrt_uses_same_hardware_srdf_and_envelope(problem):
    start=nominal_state(problem.layout);target=[start[j] for j in joint_names('right_rear')];target[-1]+=.01
    request=problem.normalize(dict(start=start,goals={'right_rear':target}))
    path,error=problem.rrt(request,4,3.)
    assert path is not None,error
    assert problem.time_parameterize(request,path)['points']


def test_native_stop_transport_sends_only_stop_to_local_fake_server():
    import socket,threading
    from uwa_cell_motion.hardware_state import dashboard_stop
    server=socket.socket();server.bind(('127.0.0.1',0));server.listen();commands=[]
    def serve():
        connection,_=server.accept()
        with connection:
            connection.sendall(b'Connected: test Dashboard\n');data=b''
            while not data.endswith(b'\n'):data+=connection.recv(100)
            commands.append(data);connection.sendall(b'Stopped\n')
    worker=threading.Thread(target=serve);worker.start()
    try:assert dashboard_stop(dict(ip='127.0.0.1',dashboard_port=server.getsockname()[1]))=='Stopped'
    finally:worker.join(timeout=2.);server.close()
    assert commands==[b'stop\n']


def test_native_stop_mock_never_connects_and_invalid_target_preserves_other_stops(monkeypatch,tmp_path):
    import yaml
    from uwa_cell_motion import native_stop
    monkeypatch.setenv('ROS_AUTOMATIC_DISCOVERY_RANGE','LOCALHOST');monkeypatch.setenv('ROS_DOMAIN_ID','67')
    file=tmp_path/'inventory.yaml';file.write_text(yaml.safe_dump({'robots':{'a':{'ip':'127.0.0.1'},'b':{'ip':'invalid'}}}))
    calls=[]
    monkeypatch.setattr(native_stop,'dashboard_stop',lambda p:calls.append(p) or 'Stopped')
    result=native_stop.stop_all(file,'mock');assert not calls and result['a']['mock'] and not result['b']['acknowledged']
    monkeypatch.setenv('ROS_DOMAIN_ID','66');result=native_stop.stop_all(file,'hardware')
    assert len(calls)==1 and result['a']['acknowledged'] and not result['b']['acknowledged']


def test_native_stop_import_does_not_depend_on_ros_or_robot_kinematics():
    import subprocess
    script="import sys; from uwa_cell_motion import native_stop; assert all(n not in sys.modules for n in ('rclpy','numpy','match_ur_hardware','uwa_cell_motion.hardware_model'))"
    subprocess.run([sys.executable,'-c',script],check=True,timeout=5.)


def test_simulation_plan_cannot_be_sent_to_hardware_backend(monkeypatch,tmp_path):
    from uwa_cell_motion.hardware_execution import execute
    monkeypatch.setenv('ROS_DOMAIN_ID','67');monkeypatch.setenv('ROS_AUTOMATIC_DISCOVERY_RANGE','LOCALHOST')
    with pytest.raises(ValueError,match='explicitly bound'):
        execute(dict(success=True,simulation_only=True),tmp_path/'result.json','mock')


def test_unknown_finger_visuals_and_simulator_actuators_are_absent_from_hardware_model(problem):
    root=ET.fromstring(problem.description)
    assert root.find('gazebo') is None and root.find('ros2_control') is None
    for row in problem.envelope_audit:
        assert not root.find(f"link[@name='{row['link']}']").findall('visual')


def test_offline_hardware_preview_labels_backend_and_unmeasured_reserve(problem,tmp_path):
    from uwa_cell_motion.preview import render
    start=nominal_state(problem.layout);target=[start[j] for j in joint_names('right_rear')];target[-1]+=.003
    plan=problem.plan(dict(start=start,goals={'right_rear':target}),'rrtconnect');plan['execution_mode']='hardware'
    output=tmp_path/'preview.html';render(plan,output);text=output.read_text()
    assert 'HARDWARE — PTP preview' in text and 'reserve UNMEASURED' in text and 'no motion sent' in text


def test_rtde_frequency_is_validated_before_connecting(monkeypatch):
    import pytest
    for hz in (0,501,float('nan'),True):
        with pytest.raises(ValueError):MotionOutputReader('must-not-connect',frequency_hz=hz)
