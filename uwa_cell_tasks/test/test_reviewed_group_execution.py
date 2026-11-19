"""Review, actual pilot interlock and two real ROS message goals with local fakes.

No ROS context, nodes, IP addresses, robot I/O or controller services are used.
The normal ApproachClient health, time alignment, targeted reset, controller
activation, final-stop verification and review-store code operate unchanged.
"""
from contextlib import nullcontext
from concurrent.futures import Future
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace as Box
import uuid

import numpy as np
import pytest
from action_msgs.msg import GoalStatus
from std_msgs.msg import String
from sensor_msgs.msg import JointState

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'tools'))
from run_carton_pregrasp import ApproachClient, read_gripper_status
from uwa_cell_gripper_control.api import endpoint
from uwa_cell_motion import hardware_execution, hardware_state
from uwa_cell_motion.common import ROBOT_IDS, joint_names
from uwa_cell_motion.execution import MotionClient
from uwa_cell_motion.hardware_ports import HOLD
from uwa_cell_motion.pilot_interlock import PilotGuardChannel
from uwa_cell_tasks import reviewed_carton_execution as execution
from uwa_cell_tasks.motion_review import ReviewStore, TASK, START_PERCENT
from uwa_cell_tasks.reviewed_carton import write_bundle, read_bundle, file_hash


ARMS = ('right_front','right_rear')
TRAJECTORY = 'scaled_joint_trajectory_controller'


def completed(value):
    future = Future()
    future.set_result(value)
    return future


def problem():
    xml = []
    names = {r:joint_names(r) for r in ROBOT_IDS}
    for arm in ROBOT_IDS:
        parent = 'world'
        for i,name in enumerate(names[arm]):
            child=f'{arm}_link_{i}'
            xml.append(f'<joint name="{name}" type="revolute"><parent link="{parent}"/><child link="{child}"/>'
                       '<axis xyz="0 0 1"/></joint>')
            parent=child
        for child in (arm+'_tool0', arm+'_robotiq_85_base_link'):
            xml.append(f'<joint name="to_{child}" type="fixed"><parent link="{parent}"/><child link="{child}"/>'
                       '<origin xyz=".02 0 0"/></joint>')
            parent=child
    return Box(names=names, original_description='<robot name="mock">'+''.join(xml)+'</robot>',
               profiles={r:dict(namespace='/'+r,ip=r,joint_names=names[r]) for r in ROBOT_IDS},
               cfg=dict(heartbeat_timeout_s=.25,state_timeout_s=.2,stop_latency_s=1.,goal_tolerance_rad=.001,
                        velocity_limit_rad_s=.1,standstill_velocity_rad_s=.001),
               signature='cell-model',binding='mock-cell', collision=Box(check=lambda state:(True, [])))


class Fixture:
    def __init__(self, problem, mode):
        self.problem, self.mode = problem, mode
        self.signature = hardware_state.signature(problem,'hardware')
        self.instance = uuid.uuid4().hex
        self.channel = PilotGuardChannel(problem, 'hardware', self.signature, self.instance)
        self.held = set(ROBOT_IDS)
        self.active = set()
        self.goals = {}
        self.stops = []
        self.cancelled = []
        self.moved = set()
        self.q = {r:np.zeros(6) for r in ROBOT_IDS}
        self.v = {r:np.zeros(6) for r in ROBOT_IDS}
        self.sequence = 0
        self.revoke = None
        self.closed_observers = set()
        self.jaw_receivers = {}
        self.jaw_queue = {}
        self.jaw_messages = []
        self.last_jaw_poll = time.monotonic()
        self.jaw_fault = False

    def jaw_status(self, arm):
        registers=dict(ACT=1, STA=3, OBJ=3, FLT=0, PRE=0, POS=0)
        if arm == ARMS[1] and self.jaw_fault:
            registers.update(OBJ=2, PRE=255, POS=181)
        return dict(observed=True, busy=False, registers=registers)

    def subscribe(self, kind, topic, receive, qos):
        for arm in ARMS:
            if topic == endpoint(arm,'hardware')+'/status':
                self.jaw_receivers[arm] = receive

    def rpc(self, _, name):
        arm = next((r for r in ROBOT_IDS if r in name),None)
        def call(_):
            if name.endswith('/read'):
                # Native GripperNode.read publishes the same device response
                # returned to the read-only service caller.
                status=self.jaw_status(arm)
                self.jaw_queue[arm]=status
                answer=Box(success=True,message=json.dumps(status))
            elif name.endswith('/reset'):
                self.held.discard(arm)
                answer=Box(success=True,message='released')
            elif name.endswith('/stop'):
                self.held.add(arm)
                self.active.discard(arm)
                self.stops.append(arm)
                answer=Box(success=True,message='held')
            elif name.endswith('list_hardware_components'):
                interfaces=[Box(name=j+'/position') for j in joint_names(arm)]
                answer=Box(component=[Box(plugin_name='ur_robot_driver/URPositionHardwareInterface',command_interfaces=interfaces)])
            elif name.endswith('list_controllers'):
                answer=Box(controller=[Box(name=TRAJECTORY,state='active' if arm in self.active else 'inactive',claimed_interfaces=[]),
                                       Box(name=HOLD,state='active' if arm in self.held else 'inactive',claimed_interfaces=[])])
            elif name.endswith('switch_controller'):
                assert arm not in self.held
                self.active.add(arm)
                answer=Box(ok=True)
            else:
                pytest.fail('Unexpected fake RPC '+name)
            return completed(answer)
        return Box(service_is_ready=lambda:True,call_async=call)

    def action(self, path):
        arm=next(r for r in ARMS if r in path)
        def send(goal):
            assert arm in self.active and arm not in self.held
            stamp=goal.trajectory.header.stamp
            start=stamp.sec+stamp.nanosec/1e9
            last=goal.trajectory.points[-1]
            duration=last.time_from_start.sec+last.time_from_start.nanosec/1e9
            accepted=self.mode!='reject' or arm!=ARMS[1]
            response=Future()
            self.goals[arm]=Box(start=start, sent=time.time(), duration=duration, goal=goal,
                                result=response,accepted=accepted, origin=self.q[arm].copy())
            if self.mode == 'revoke_first' and self.revoke:
                self.revoke()
                self.revoke = None
            if self.mode == 'missing_ack' and arm == ARMS[1]:
                return Future()  # the peer may already have queued the goal
            handle=Box(accepted=accepted,get_result_async=lambda:response,
                       cancel_goal_async=lambda:self.cancelled.append(arm))
            return completed(handle)
        return Box(server_is_ready=lambda:True,send_goal_async=send)

    def spin(self, client, timeout):
        if timeout:
            time.sleep(min(timeout, .001))
        now, wall = time.monotonic(), time.time()
        self.sequence += 1
        for arm,item in self.goals.items():
            self.v[arm] = np.zeros(6)
            if arm not in self.active or not item.accepted:
                continue
            u = np.clip((wall-item.start)/item.duration, 0.,1.)
            delta=np.array(item.goal.trajectory.points[-1].positions)-item.origin
            self.q[arm]=item.origin+delta*(10*u**3-15*u**4+6*u**5)
            self.v[arm]=delta*30*u**2*(1-u)**2/item.duration
            if u>0:
                self.moved.add(arm)
            if u==1 and not item.result.done():
                item.result.set_result(Box(status=GoalStatus.STATUS_SUCCEEDED,result=Box(error_code=0,error_string='')))
        if self.revoke and ((self.mode=='revoke' and self.moved) or (self.mode=='revoke_queued' and self.goals)):
            self.revoke()
            self.revoke=None
        if self.mode=='jaw_closed' and self.moved and not self.jaw_fault:
            self.jaw_fault=True
            self.jaw_queue[ARMS[1]]=self.jaw_status(ARMS[1])
        if now-self.last_jaw_poll>=1.:
            self.last_jaw_poll=now
            self.jaw_queue.update({arm:self.jaw_status(arm) for arm in self.jaw_receivers})
        for arm,status in self.jaw_queue.items():
            if arm in self.jaw_receivers:
                self.jaw_receivers[arm](String(data=json.dumps(status)))
                self.jaw_messages.append((arm,status['registers']['OBJ']))
        self.jaw_queue.clear()

        records={r:dict(received=now,source_stamp=now-.001,epoch=0,q=q.tolist(),v=self.v[r].tolist(),
                        status=dict(safety_mode=1,runtime_state=2,robot_mode=7)) for r,q in self.q.items()}
        model={j:x for r,n in self.problem.names.items() for j,x in zip(n,self.q[r].tolist())}
        quiet=[r for r in ROBOT_IDS if not np.any(self.v[r])]
        supervisor=dict(armed=True,witness_available=True,held_arms=sorted(self.held),blocked_arms=sorted(self.held),
                        ports={r:dict(manager_fresh=True,hardware_mode_verified=True,hold_config_verified=True,
                                      held=r in self.held) for r in ROBOT_IDS})
        guard=dict(armed=True,faults=[],model_match=True,stationary_arms=quiet,blocked_arms=sorted(self.held))
        faults,guard['pilot']=self.channel.tick(now,records,guard,supervisor,True)
        if faults:
            self.held.update(ROBOT_IDS)
            self.active.clear()
        header=dict(hardware_signature=self.signature,armed=True,instance=self.instance,
                    sequence=self.sequence,evaluated_monotonic_s=now)
        def message(value):
            return String(data=json.dumps({**header,**value}))
        client.state(message(dict(records=records,model_state=model,model_signature=self.problem.signature,assembled_wall_time_s=wall)))
        client.guard_message(message(guard))
        client.supervisor_message(message(supervisor))
        for arm in ARMS:
            sample=JointState(name=joint_names(arm),position=self.q[arm].tolist(),velocity=self.v[arm].tolist())
            sample.header.stamp.sec,sample.header.stamp.nanosec=divmod(round(wall*1e9),10**9)
            client.driver_state(arm,sample)

    def Observer(self, arm):
        cell=self
        class Trace:
            error=None

            def __init__(self):
                self.lock=threading.Lock()
                self.rows=[]
                self.done=threading.Event()
                self.worker=threading.Thread(target=self.collect,daemon=True)
                self.worker.start()

            def collect(self):
                origin=time.monotonic()
                while not self.done.is_set():
                    now=time.monotonic()
                    force=[0.,0.,4.,0.,0.,0.]
                    if arm==ARMS[1] and cell.mode=='wrench_fault' and cell.moved:
                        force[2]+=13.
                    row=dict(received=now,device_stamp=now-origin,q=cell.q[arm].tolist(),v=cell.v[arm].tolist(),
                             force=force,status=dict(robot_mode=7,runtime_state=2,safety_mode=1))
                    with self.lock:
                        self.rows.append(row)
                    self.done.wait(.05)  # Native force reader publishes at 20 Hz.

            def snapshot(self):
                with self.lock:return list(self.rows)

            def close(self):
                self.done.set()
                self.worker.join()
                cell.closed_observers.add(arm)
        return Trace()


@pytest.mark.parametrize('mode',['success','slow_geometry','reject','missing_ack','revoke','revoke_queued','revoke_first',
                                'jaw_closed','wrench_fault'])
def test_review_to_two_controller_results_without_ros(monkeypatch,tmp_path,mode):
    p=problem()
    fixture=Fixture(p,mode)
    store=ReviewStore(tmp_path/'authority')
    store.area('new',True)
    start={j:0. for joints in p.names.values() for j in joints}
    trajectories={}
    for arm in ARMS:
        points=[dict(time=t,positions=[0.]*5+[q],velocities=[0.]*6,accelerations=[0.]*6)
                for t,q in [(0,0),(.10,.002)]]
        trajectories[arm]=dict(joint_names=joint_names(arm),points=points,waypoints=[v['positions'] for v in points],
                               duration_s=.10)
    group=dict(arms=list(ARMS),start=start,trajectories=trajectories,duration_s=.10)
    path=tmp_path/'bundle.json'
    model=tmp_path/'model.urdf'
    model.write_text(p.original_description)
    source=tmp_path/'source.json'
    source.write_text('{}')
    write_bundle(path,'entry',p,start,[group],[],source,model,{},.1,.25/3)
    sha=file_hash(path)
    release=store.submit('fixture/motion',dict(task=TASK,stage='motion',risk='medium',reason='group near carton',
                          speed_percent=START_PERCENT,components=[sha],explicit_regular_start=False),{})
    store.decide(release,store.export(release)['sha256'],'approve')
    assert store.claim(release)
    session=store.status()['session_id']
    fixture.revoke=lambda:store.area(session,False)
    # Replace only transports, constructor and the ROS context. The deployed
    # runner still takes the bound hardware path and sends typed ROS goals.
    monkeypatch.setattr(execution,'ReviewStore',lambda:store)
    monkeypatch.setattr(execution,'motion_context',nullcontext)
    monkeypatch.setattr(execution,'require_domain',lambda mode:None)
    monkeypatch.setattr(hardware_execution,'require_domain',lambda mode:None)
    monkeypatch.setattr(hardware_execution.MotionNode,'__init__',lambda self,*args,**opts:None)
    monkeypatch.setattr(hardware_execution,'ActionClient',lambda node,typ,path:fixture.action(path))
    monkeypatch.setattr(hardware_execution,'SingleThreadedExecutor',lambda:Box(add_node=lambda n:None))
    monkeypatch.setattr(hardware_execution.HardwareClient,'start_driver_receiver',lambda self:None)
    monkeypatch.setattr(MotionClient,'spin_once',lambda self,timeout_sec=.01:fixture.spin(self,timeout_sec))
    monkeypatch.setattr(hardware_execution,'stop_profiles',lambda *args:pytest.fail('Unexpected native STOP fallback'))
    class Client(ApproachClient):
        def create_subscription(self,*args,**kwargs):return fixture.subscribe(*args,**kwargs)
        def create_client(self,kind,name):return fixture.rpc(kind,name)
        def destroy_node(self):return True
        def get_clock(self):return Box(now=lambda:Box(nanoseconds=time.time_ns()))
    args=Box(review_id=release,reviewed_sha256=sha,start_ros_programs=False)
    report={}
    if mode=='slow_geometry':
        original_monitor=execution._monitor
        delayed={'done':False}
        def slow_monitor(client,*args,**kwargs):
            if kwargs.get('geometry',True) and not delayed['done']:
                assert set(client.handles)==set(ARMS)
                delayed['done']=True
                time.sleep(.13)  # exceeds acceptance window, still before common start
            return original_monitor(client,*args,**kwargs)
        monkeypatch.setattr(execution,'_monitor',slow_monitor)
    try:
        bundle=read_bundle(path,sha,'entry',p,source)
        rc=execution.run_bundle(p,bundle,args,tmp_path,report,client_type=Client,observer_type=fixture.Observer,
                                read_gripper=read_gripper_status,start_programs=lambda *a:pytest.fail('Unexpected Play'),
                                end_phase='OPEN_HELD',extra_collision=p.collision)
        expected = {ARMS[0]} if mode == 'revoke_first' else set(ARMS)
        assert set(fixture.goals)==expected,report.get('error')
        if len(expected)==2:
            assert fixture.goals[ARMS[0]].start==fixture.goals[ARMS[1]].start
        assert all(g.sent<g.start for g in fixture.goals.values())
        assert not fixture.active and set(fixture.stops)>=set(ARMS) and set(fixture.held)==set(ROBOT_IDS)
        assert fixture.closed_observers==set(ARMS)
        assert {arm for arm,obj in fixture.jaw_messages if obj==3} == set(ARMS)
        for arm in ARMS:
            native=json.loads((tmp_path/(arm+'-native.json')).read_text())['records']
            times=np.array([row['received'] for row in native])
            assert len(times)>=10 and np.all(np.diff(times)>0) and times[-1]-times[0]>=.45
        final=store.finish(release,rc==0)
        if mode in ('success','slow_geometry'):
            assert rc==0 and final=='done' and report['segments'][0]['executed'],report.get('error')
            assert fixture.moved==set(ARMS)
            for arm in ARMS:
                assert fixture.q[arm][-1]==pytest.approx(.002)
        else:
            assert rc!=0 and final=='failed' and not report['segments'][0]['executed']
            if mode=='reject':
                assert 'trajectory rejected' in report['error']
                assert ARMS[0] in fixture.cancelled and not fixture.moved
            elif mode=='missing_ack':
                assert 'group acceptance' in report['error']
                assert not fixture.moved
            elif mode=='revoke':
                assert 'revoked' in report['error'] and fixture.moved
            elif mode=='jaw_closed':
                assert (ARMS[1],2) in fixture.jaw_messages and 'open-jaw registers lost' in report['error']
            elif mode=='wrench_fault':
                assert 'unexpected wrench' in report['error'] and fixture.moved
            else:
                assert 'revoked' in report['error'] and not fixture.moved
    finally:
        fixture.channel.close()


def test_ready_but_late_acceptance_does_not_relax_deadline(monkeypatch):
    monkeypatch.setattr(execution.time,'monotonic',lambda:1.)
    client=Box(pending={'right_front':completed(Box(accepted=True))},handles={},
               get_clock=lambda:Box(now=lambda:Box(nanoseconds=0)))
    segment={'goal_response_observed_monotonic_s_by_arm':{},'goal_accept_observed_monotonic_s_by_arm':{}}
    with pytest.raises(TimeoutError,match='timely group acceptance'):
        execution._accept_responses(client,{},segment,.9,200_000_000)
    assert not client.handles
