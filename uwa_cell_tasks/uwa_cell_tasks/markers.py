"""Explicit source labels; estimated and simulator poses never share a frame."""
import json
import numpy as np
from scipy.spatial.transform import Rotation
from visualization_msgs.msg import Marker,MarkerArray


def object_markers(node,scene,truth,status,group):
    array=MarkerArray();marker=Marker();marker.header.frame_id='world';marker.header.stamp=node.get_clock().now().to_msg()
    marker.ns='task_state';marker.id=0;marker.type=Marker.TEXT_VIEW_FACING;marker.action=Marker.ADD
    marker.pose.position.z=1.8;marker.pose.orientation.w=1.;marker.scale.z=.06
    marker.color.r=1.;marker.color.g=1.;marker.color.b=1.;marker.color.a=1.
    marker.text='SIMULATION / '+status['state']+'\n'+('RIGID OBJECT GROUP: RF + RR' if group else 'NO LOADED GROUP')
    marker.lifetime.sec=1;array.markers.append(marker)
    if truth:
        t=np.array(truth['T_world_object']);m=Marker();m.header=marker.header;m.ns='simulation_truth';m.id=1
        m.type=Marker.MESH_RESOURCE;m.action=Marker.ADD
        m.mesh_resource='package://uwa_cell_description/assets/carton_avocado_v1/carton.dae';m.mesh_use_embedded_materials=True
        m.pose.position.x,m.pose.position.y,m.pose.position.z=map(float,t[:3,3])
        q=Rotation.from_matrix(t[:3,:3]).as_quat();m.pose.orientation.x,m.pose.orientation.y,m.pose.orientation.z,m.pose.orientation.w=map(float,q)
        m.scale.x=m.scale.y=m.scale.z=1.;m.color.a=1.;m.lifetime.sec=1;array.markers.append(m)
    return array
