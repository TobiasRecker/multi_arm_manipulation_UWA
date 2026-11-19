"""Driver acquisition must continue while the task thread is occupied."""
import threading,time
from types import SimpleNamespace
import numpy as np
import pytest
from sensor_msgs.msg import JointState
from uwa_cell_motion.node import MotionNode
from uwa_cell_motion.driver_history import DriverHistoryReceiver
from uwa_cell_motion.state_alignment import aligned_driver
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.common import joint_names
from uwa_cell_motion.hardware_execution import HardwareClient


def test_two_driver_histories_survive_blocked_task_thread(monkeypatch):
    monkeypatch.setenv('ROS_DOMAIN_ID','77');monkeypatch.setenv('ROS_AUTOMATIC_DISCOVERY_RANGE','LOCALHOST')
    arms=['right_front','right_rear'];profiles={a:dict(namespace='/driver_history_test/'+a)for a in arms}
    rows={a:[]for a in arms};lock=threading.Lock();done=threading.Event()
    def receive(arm,msg):
        stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9
        with lock:rows[arm].append((stamp,list(msg.position)))
    with motion_context():
        publisher=MotionNode('driver_history_source')
        pubs={a:publisher.create_publisher(JointState,profiles[a]['namespace']+'/joint_states',10)for a in arms}
        receiver=DriverHistoryReceiver(profiles,arms,receive);base=time.time()
        def produce():
            while not done.is_set():
                stamp=time.time_ns();q=.1*(stamp/1e9-base)
                for a,pub in pubs.items():
                    msg=JointState(name=joint_names(a),position=[q]*6,velocity=[.1]*6)
                    msg.header.stamp.sec,msg.header.stamp.nanosec=divmod(stamp,10**9);pub.publish(msg)
                done.wait(.002)
        worker=threading.Thread(target=produce);worker.start()
        try:
            end=time.monotonic()+3.
            while time.monotonic()<end:
                with lock:ready=all(len(rows[a])>=15 for a in arms)
                if ready:break
                time.sleep(.005)
            assert ready
            with lock:counts={a:len(rows[a])for a in arms}
            # No task-executor spin during this pause, longer than the old
            # 124ms gap which consumed the unchanged 5mrad comparison budget.
            time.sleep(.15)
            with lock:captured={a:list(rows[a])for a in arms}
            for a,history in captured.items():
                assert len(history)-counts[a]>=25
                target=history[-1][0]-.03
                aligned=aligned_driver(history,target,np.ones(6)*.105,.2)
                certified=abs(np.asarray(aligned['q'])-.1*(target-base))+aligned['uncertainty_rad']
                assert max(certified)<.005
            assert receiver.error is None
        finally:
            done.set();worker.join(timeout=1.);receiver.close();publisher.destroy_node()
        assert not receiver.worker.is_alive()


def test_failed_receiver_is_a_health_failure_before_any_motion():
    client=SimpleNamespace(spin_once=lambda **kw:None,cfg={'state_timeout_s':.2},
                           driver_receiver=SimpleNamespace(error='decoder failure'))
    with pytest.raises(RuntimeError,match='Driver history receiver failed: decoder failure'):
        HardwareClient.health(client)
