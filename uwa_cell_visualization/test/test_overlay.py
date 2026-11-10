from copy import deepcopy
import math
from pathlib import Path
import threading
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest
from rclpy.time import Time
from sensor_msgs.msg import JointState

from uwa_cell_visualization.model import ARMS,EMPTY_MODEL,JOINTS,description,load_inputs,map_positions,paths
from uwa_cell_visualization.bridge import MeasuredOverlay


def inputs():
    return load_inputs(Path(__file__).resolve().parents[2]/'config/hardware_inventory.yaml',paths(),ARMS)


def mount_transform(robot):
    # Only fixed joints from world to the mounting base_link, including table rotation.
    joints={j.find('child').get('link'):j for j in robot.findall('joint')}
    base=next(link.get('name') for link in robot.findall('link') if link.get('name').endswith('_base_link'))
    chain=[]
    while base!='world':
        joint=joints[base];chain.append(joint);base=joint.find('parent').get('link')
    import numpy as np
    from scipy.spatial.transform import Rotation
    result=np.eye(4)
    for joint in reversed(chain):
        origin=joint.find('origin');step=np.eye(4)
        step[:3,3]=list(map(float,origin.get('xyz').split()))
        step[:3,:3]=Rotation.from_euler('xyz',list(map(float,origin.get('rpy').split()))).as_matrix()
        result=result@step
    return result


def test_models_unique_joints_no_control_plugins_correct_mounts():
    profiles,layout=inputs();names=[]
    for rid,y in [('right_front',-.675),('right_rear',.675)]:
        text=description(profiles[rid],layout);robot=ET.fromstring(text)
        movable=[j for j in robot.findall('joint') if j.get('type')=='revolute']
        assert len(movable)==6
        assert all(j.get('name').startswith('real_'+rid+'_') for j in movable)
        names.extend(j.get('name') for j in movable)
        assert robot.find('ros2_control') is None and robot.find('gazebo') is None
        assert 'ur5e/collision/' in text
        assert all(link.get('name')=='world' or link.get('name').startswith('real_') for link in robot.findall('link'))
        assert mount_transform(robot)[:3,3]==pytest.approx([.45,y,.9])
    assert len(set(names))==12


def test_moving_table_moves_both_models_and_display_offset_is_separate():
    profiles,layout=inputs()
    changed=deepcopy(layout);changed['tables']['right']['xyz'][0]+=1.2
    for rid in ARMS:
        original=mount_transform(ET.fromstring(description(profiles[rid],layout)))
        moved=mount_transform(ET.fromstring(description(profiles[rid],changed,(.3,0,0))))
        assert moved[0,3]-original[0,3]==pytest.approx(1.5)
        assert moved[1,3]==pytest.approx(original[1,3])


def test_only_complete_finite_source_joints_are_mapped_in_canonical_order():
    profiles,_=inputs();profile=profiles['right_rear'];names=profile['joint_names']
    assert map_positions(names[::-1],list(range(6))[::-1],profile)==list(range(6))
    for n,q in [(names,[0]*5),(names[:-1],[0]*5),(names,[0,0,math.nan,0,0,0]),
                ([names[0]]*6,[0]*6),(['real_'+name for name in names],[0]*6)]:
        with pytest.raises((ValueError,KeyError)):map_positions(n,q,profile)


class Publisher:
    def __init__(self):self.messages=[]
    def publish(self,msg):self.messages.append(msg)


def test_no_initial_pose_and_stale_data_hides_model_even_if_simulation_clock_paused(monkeypatch):
    import uwa_cell_visualization.bridge as bridge
    profiles,layout=inputs();rid='right_rear'
    overlay=MeasuredOverlay.__new__(MeasuredOverlay)
    overlay.profiles={rid:profiles[rid]};overlay.layout=layout;overlay.models={rid:'<robot/>'}
    overlay.stale_after=2.;overlay.offset=(0,0,0);overlay.lock=threading.Lock()
    overlay.samples={};overlay.errors={};overlay.sequence=0;overlay.sent={};overlay.visible={rid:False}
    overlay.state_pub={rid:Publisher()};overlay.description_pub={rid:Publisher()}
    overlay.marker_pub=Publisher();overlay.status_pub=Publisher();overlay.last_status=0
    overlay.target=SimpleNamespace(get_clock=lambda:SimpleNamespace(now=lambda:Time(seconds=17)))
    overlay.source_domain=66;overlay.target_domain=64
    now=[100.];monkeypatch.setattr(bridge.time,'monotonic',lambda:now[0])
    overlay.publish()
    assert not overlay.state_pub[rid].messages
    assert 'WAITING' in overlay.status_pub.messages[-1].data
    msg=JointState();msg.name=profiles[rid]['joint_names'];msg.position=[.1]*6
    msg.header.stamp.sec=1794290000  # Wall-clock input must not leak into simulation TF.
    overlay.receive(rid,msg);overlay.publish()
    output=overlay.state_pub[rid].messages[-1]
    assert output.header.stamp.sec==17
    assert all(name.startswith('real_right_rear_') for name in output.name)
    assert overlay.description_pub[rid].messages[-1].data=='<robot/>'
    now[0]+=3.;overlay.publish()
    assert overlay.description_pub[rid].messages[-1].data==EMPTY_MODEL
    assert 'STALE' in overlay.status_pub.messages[-1].data
