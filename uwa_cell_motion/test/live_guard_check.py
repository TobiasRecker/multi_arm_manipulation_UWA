"""Explicit Gazebo-only integration check; run with ordinary guard stopped.

Starts its own geometric guard fixture against the real simulated JointStates.
Only this fixture alters reported clearances/freshness. No fault-injection
interface is exposed by the installed production nodes. Existing supervisor
and four loaded hold controllers are required. Leaves all arms held on exit.
"""
import argparse
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

import numpy as np
import rclpy
from sensor_msgs.msg import JointState
from rclpy.qos import qos_profile_sensor_data
from std_srvs.srv import Trigger
from std_msgs.msg import String
from controller_manager_msgs.srv import ListControllers
from trajectory_msgs.msg import JointTrajectory

from uwa_cell_motion.common import config,dump,simulation_only,ROBOT_IDS,joint_names
from uwa_cell_motion.execution import MotionClient
from uwa_cell_motion.supervisor import hold_name


def fixture(path):
    from uwa_cell_motion.guard_node import CollisionGuard
    class TestGuard(CollisionGuard):
        def __init__(self):
            self.flags={};super().__init__(config())
            original=self.core.fresh
            self.core.fresh=lambda rid,now,source:rid not in self.flags.get('stale_arms',[]) and original(rid,now,source)
        def tick(self):
            self.flags=json.loads(Path(path).read_text());super().tick()
        def geometry(self,now):
            world,pairs=super().geometry(now)
            for index in self.flags.get('pair_faults',[]):pairs[index]['clearance_m']=pairs[index]['threshold_m']-.001
            return world,pairs
    rclpy.init();node=TestGuard()
    try:rclpy.spin(node)
    finally:node.destroy_node();rclpy.shutdown()


def check(output):
    simulation_only();cfg=config();results={};rclpy.init();node=MotionClient()
    trace=[]
    node.create_subscription(String,'/uwa_cell/collision_guard/decision',lambda msg:trace.append(json.loads(msg.data)),10)
    child=None
    with tempfile.TemporaryDirectory(prefix='uwa-guard-live-') as directory:
        flags=Path(directory)/'faults.json';dump(flags,{})
        log=open(Path(output).with_suffix('.fixture.log'),'w')
        try:
            child=subprocess.Popen([sys.executable,__file__,'--fixture',str(flags)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            node.connect()
            node.wait(lambda:set(node.supervisor['held_arms'])==set(ROBOT_IDS),5.)
            def wait_seconds(seconds):
                end=time.monotonic()+seconds;node.wait(lambda:time.monotonic()>=end,seconds+2.)
            def reset():
                wait_seconds(.5)
                answer=node.service(Trigger,'/uwa_cell/collision_supervisor/reset',Trigger.Request())
                assert answer.success,answer.message
                node.wait(lambda:not node.supervisor['blocked_arms'] and not node.supervisor['held_arms'],3.)
            def controllers():
                answer=node.service(ListControllers,'/uwa_cell/controller_manager/list_controllers',ListControllers.Request())
                return {c.name:c.state for c in answer.controller}
            reset();start=dict(node.positions);arms=['left_front','right_front','left_rear']
            telemetry=[]
            def sample(msg):
                velocity=dict(zip(msg.name,msg.velocity))
                telemetry.append((time.monotonic(),max(abs(velocity.get(j,0.)) for r in ('left_front','right_front') for j in joint_names(r))))
            node.create_subscription(JointState,'/uwa_cell/joint_states',sample,qos_profile_sensor_data)
            targets={r:np.array([start[j] for j in joint_names(r)])+np.array([0,0,0,0,0,.12]) for r in arms}
            node.activate(arms);injected=[]
            def inject():
                injected.append(time.monotonic());dump(flags,dict(pair_faults=[0]))
            timer=threading.Timer(.7,inject);timer.start()
            stops=node.phase(targets,cfg,set());timer.join()
            node.wait(lambda:set(node.supervisor['held_arms'])=={'left_front','right_front'},2.)
            assert set(stops)=={'left_front','right_front'},stops
            peak=max(v for t,v in telemetry if t<injected[0])
            assert peak>cfg['standstill_velocity_rad_s']
            stopped_at=next(t for t,v in telemetry if t>=injected[0] and v<=cfg['standstill_velocity_rad_s'])
            results['pair_fault_to_standstill_s']=stopped_at-injected[0]
            assert results['pair_fault_to_standstill_s']<=1/cfg['rate_hz']+cfg['stop_latency_s']+peak/cfg['braking_acceleration_rad_s2']+.1
            assert max(abs(node.positions[j]-targets['left_rear'][i]) for i,j in enumerate(joint_names('left_rear')))<.001
            assert max(abs(node.positions[j]-targets['left_front'][i]) for i,j in enumerate(joint_names('left_front')))>.02
            results['pair_stop_independent_arm_continues']=True
            states=controllers();assert states[hold_name('left_front')]=='active' and states['left_rear_trajectory_controller']=='active'

            before=dict(node.positions);publisher=node.create_publisher(JointTrajectory,'/uwa_cell/left_front_trajectory_controller/joint_trajectory',10)
            from trajectory_msgs.msg import JointTrajectoryPoint
            command=JointTrajectory();command.joint_names=joint_names('left_front')
            point=JointTrajectoryPoint();point.positions=[before[j]+.02 for j in command.joint_names];point.time_from_start.sec=1
            command.points=[point]
            for _ in range(5):publisher.publish(command);wait_seconds(.05)
            wait_seconds(.5)
            assert max(abs(node.positions[j]-before[j]) for j in command.joint_names)<.001
            try:node.switch(['left_front_trajectory_controller'],[]);activation_refused=False
            except RuntimeError:activation_refused=True
            assert activation_refused and controllers()[hold_name('left_front')]=='active'
            results['topic_and_reactivation_interlock']=True

            dump(flags,{});wait_seconds(.5)
            assert set(node.supervisor['blocked_arms'])=={'left_front','right_front'}
            results['no_automatic_resume']=True;reset()
            dump(flags,dict(pair_faults=[0,1]))
            node.wait(lambda:set(node.supervisor['held_arms'])=={'left_front','right_front','left_rear'},3.)
            results['simultaneous_pair_union']=True
            dump(flags,{});reset();dump(flags,dict(stale_arms=['left_front']))
            node.wait(lambda:node.guard['state']=='STATE STALE' and set(node.supervisor['held_arms'])=={'left_front','right_front','left_rear'},3.)
            results['lost_state_neighbor_scope']=True
            dump(flags,{});reset()
            # No MotionClient health/stop fallback during this observation:
            # the independent supervisor alone must react to missing decisions.
            began=time.monotonic();child.send_signal(signal.SIGSTOP)
            node.wait(lambda:set(node.supervisor['held_arms'])==set(ROBOT_IDS),3.)
            latency=time.monotonic()-began
            assert latency<=cfg['heartbeat_timeout_s']+cfg['stop_latency_s']+.15
            results['guard_loss_hold_latency_s']=latency
            child.send_signal(signal.SIGCONT);wait_seconds(.5)
            assert set(node.supervisor['blocked_arms'])==set(ROBOT_IDS)
            results['heartbeat_recovery_stays_latched']=True
            results['success']=True;results['final_positions']=dict(node.positions)
        except BaseException as error:
            import traceback
            results.update(success=False,error=str(error),traceback=traceback.format_exc())
            results['last_guard']=node.guard;results['last_supervisor']=node.supervisor
            results['fault_trace']=[dict(state=t['state'],blocked=t['blocked_arms'],faults=t['faults'],ages=t['state_ages_s']) for t in trace if t['faults']][-30:]
            node.stop(node.owned)
        finally:
            if child:
                child.send_signal(signal.SIGCONT);child.send_signal(signal.SIGINT)
                try:child.wait(timeout=5.)
                except subprocess.TimeoutExpired:child.kill();child.wait()
            dump(output,results);node.destroy_node();rclpy.shutdown();log.close()
    if not results['success']:raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fixture');parser.add_argument('--output')
    args=parser.parse_args()
    if args.fixture:fixture(args.fixture)
    elif args.output:check(args.output)
    else:parser.error('--output required')
