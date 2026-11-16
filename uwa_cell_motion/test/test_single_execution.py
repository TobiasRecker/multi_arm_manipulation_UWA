from pathlib import Path
import sys
import time
import numpy as np
import pytest
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.single_execution import corridor_error
from uwa_cell_motion.execution import check_stationary,_follow,settle_obstacles,drives_stationary,unclaimed_tools
from uwa_cell_motion.common import joint_names


def test_motion_node_keeps_clock_and_data_but_omits_unused_warning_waitables(monkeypatch):
    import rclpy
    from std_msgs.msg import String
    from rclpy.event_handler import PublisherEventCallbacks
    from rclpy.parameter import Parameter
    from rclpy.executors import SingleThreadedExecutor
    from uwa_cell_motion.node import MotionNode
    from uwa_cell_motion.execution import motion_context
    monkeypatch.setenv('ROS_DOMAIN_ID','64')
    with motion_context():
        node=MotionNode('motion_waitable_check')
        executor=SingleThreadedExecutor();executor.add_node(node)
        try:
            node.set_parameters([Parameter('use_sim_time',value=True)])
            received=[];publisher=node.create_publisher(String,'~/sample',10)
            subscription=node.create_subscription(String,'~/sample',lambda msg:received.append(msg.data),10)
            assert all(not entity.event_handlers for entity in list(node.publishers)+list(node.subscriptions))
            deadline=time.monotonic()+3.
            while not received and time.monotonic()<deadline:
                publisher.publish(String(data='valid'));executor.spin_once(timeout_sec=.02)
            assert received and received[-1]=='valid'
            assert any(s.topic_name=='/clock' for s in node.subscriptions)
            explicit=node.create_publisher(String,'~/explicit',10,event_callbacks=PublisherEventCallbacks(
                incompatible_qos=lambda event:None,use_default_callbacks=False))
            assert len(explicit.event_handlers)==1
        finally:executor.shutdown();node.destroy_node()


def test_rpc_response_is_serviced_under_continuously_ready_timer_load(monkeypatch):
    import rclpy
    from rclpy.clock import Clock,ClockType
    from std_srvs.srv import Trigger
    from uwa_cell_motion.execution import MotionClient,motion_context
    monkeypatch.setenv('ROS_DOMAIN_ID','64');monkeypatch.setenv('GZ_PARTITION','uwa_cell_sim')
    monkeypatch.setenv('ROS_AUTOMATIC_DISCOVERY_RANGE','LOCALHOST')
    with motion_context():
        client=MotionClient();count={'timer':0}
        try:
            def tick():count['timer']+=1
            def answer(request,response):response.success=True;return response
            timer=client.create_timer(.00001,tick,clock=Clock(clock_type=ClockType.STEADY_TIME))
            service=client.create_service(Trigger,'~/executor_fairness_check',answer)
            request=client.create_client(Trigger,'~/executor_fairness_check')
            assert request.wait_for_service(timeout_sec=3.)
            future=request.call_async(Trigger.Request());client.wait(future.done,2.)
            assert future.result().success and count['timer']>0
        finally:client.destroy_node()


def test_time_lag_on_checked_path_is_safe_but_geometric_departure_is_detected():
    vertices=np.array([[0.,0.],[1.,1.],[1.,2.]])
    start=vertices[:-1];delta=np.diff(vertices,axis=0);squared=np.sum(delta*delta,axis=1)
    assert corridor_error(np.array([.2,.2]),start,delta,squared)<1e-12
    assert corridor_error(np.array([.8,.8]),start,delta,squared)<1e-12
    assert corridor_error(np.array([.5,.7]),start,delta,squared)>.05


def test_stationary_waypoint_has_finite_corridor_distance():
    start=np.array([[1.,2.]]);delta=np.zeros((1,2));squared=np.array([1e-20])
    assert corridor_error(np.array([1.,2.]),start,delta,squared)==0
    assert np.isclose(corridor_error(np.array([1.,2.01]),start,delta,squared),.01)


def test_drive_standstill_ignores_passive_noise_but_rejects_moving_missing_nonfinite_drive():
    client=SimpleNamespace(names={'arm':['drive']},velocities={'drive':0.,'passive_mimic':.1})
    assert drives_stationary(client)
    client.velocities['drive']=.01;assert not drives_stationary(client)
    client.velocities['drive']=float('nan');assert not drives_stationary(client)
    del client.velocities['drive'];assert not drives_stationary(client)


def test_unselected_arm_requires_stationary_measured_state():
    client=SimpleNamespace(positions={'obstacle':1.,'selected':2.},velocities={'obstacle':0.,'selected':.05})
    check_stationary(client,{'obstacle':1.})
    client.velocities['obstacle']=.01
    with pytest.raises(RuntimeError,match='Stationary obstacle/tool joint moved'):check_stationary(client,{'obstacle':1.})
    client.velocities['obstacle']=0.;client.positions['obstacle']=1.002
    with pytest.raises(RuntimeError,match='Stationary obstacle/tool joint moved'):check_stationary(client,{'obstacle':1.})


def test_selected_arm_gripper_motion_invalidates_arm_only_plan_before_activation():
    names=joint_names('left_front');tool='left_front_finger_joint'
    client=SimpleNamespace(guard={'blocked_arms':[]},supervisor={'blocked_arms':[]},
        positions={j:0. for j in names+[tool]},velocities={j:(.01 if j==tool else 0.) for j in names+[tool]})
    client.health=lambda:None
    client.hold_idle_tools=lambda:[]
    def wait(predicate,**kwargs):
        assert not predicate()
        raise TimeoutError()
    client.wait=wait
    problem=SimpleNamespace(names={'left_front':names+[tool]})
    plan={'request':{'selected':['left_front']},'trajectory':{'joint_names':names}}
    with pytest.raises(RuntimeError,match='Stationary obstacle/tool joints did not settle'):_follow(problem,client,plan,{})


def test_preceding_obstacle_can_settle_before_start_without_looser_runtime_monitor(monkeypatch):
    from uwa_cell_motion import execution
    clock={'now':0.};monkeypatch.setattr(execution,'time',SimpleNamespace(monotonic=lambda:clock['now']))
    client=SimpleNamespace(velocities={'obstacle':.01,'selected':.05},health=lambda:None)
    def wait(predicate,**kwargs):
        assert not predicate()
        client.velocities['obstacle']=0.;assert not predicate()
        clock['now']=.11;assert predicate()
    client.wait=wait
    settle_obstacles(client,['obstacle'])
    assert client.velocities['selected']==.05


def test_idle_tool_hold_only_claims_configured_unowned_drive():
    names={r:[r+str(i) for i in range(6)]+[r+'_finger'] for r in ('free','held','custom')}
    controllers=[SimpleNamespace(name='free_gripper_controller',state='inactive',claimed_interfaces=[]),
        SimpleNamespace(name='held_gripper_controller',state='active',claimed_interfaces=['held_finger/position']),
        SimpleNamespace(name='custom_owner',state='active',claimed_interfaces=['custom_finger/velocity'])]
    assert unclaimed_tools(names,controllers)=={'free':'free_finger'}


def test_idle_tool_hold_never_preempts_collision_hold():
    names={'arm':['q'+str(i) for i in range(7)]}
    controllers=[SimpleNamespace(name='collision_hold',state='active',claimed_interfaces=['q6/position'])]
    assert unclaimed_tools(names,controllers)=={}


def test_unclaimed_drive_without_configured_controller_rejects_execution():
    with pytest.raises(RuntimeError,match='no configured holding controller'):
        unclaimed_tools({'arm':['q'+str(i) for i in range(7)]},[])
