"""Read-only check of the live visual asset, TF, markers and rendered camera."""
import argparse
import json
from pathlib import Path
import time

import cv2
import numpy as np
import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from scipy.spatial.transform import Rotation
from sensor_msgs.msg import Image
from tf2_msgs.msg import TFMessage
from visualization_msgs.msg import MarkerArray
from rosgraph_msgs.msg import Clock
from gz.msgs.empty_pb2 import Empty
from gz.msgs.scene_pb2 import Scene
from gz.transport import Node as Transport

from uwa_cell_description.configuration import load_layout
from uwa_cell_description.scene_assets import instances
from uwa_cell_gazebo.overview import TOPIC, camera_config, intrinsic, transforms


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--without-camera',action='store_true',help='Verify model/TF/markers while another job owns or disables the sensor')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    layout=load_layout();item=instances(layout)[0];expected=item['T_world_object']
    rclpy.init();node=rclpy.create_node('check_reconstructed_carton');latest={};clocks=[]
    qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)
    def tf(message):
        for t in message.transforms:
            if t.child_frame_id==item['frame']:latest['tf']=t
    subscriptions=[node.create_subscription(TFMessage,'/tf_static',tf,qos),
        node.create_subscription(MarkerArray,'/uwa_cell/scene_assets/markers',lambda m:latest.update(markers=m),qos),
        node.create_subscription(Image,TOPIC+'/image_raw',lambda m:latest.update(image=m),qos_profile_sensor_data),
        node.create_subscription(Clock,'/clock',lambda m:clocks.append(m.clock.sec+m.clock.nanosec*1e-9),qos_profile_sensor_data)]
    report=dict(success=False,model_name=item['model_name'])
    try:
        deadline=time.monotonic()+35
        while time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.1)
            needed={'tf','markers'} if args.without_camera else {'tf','markers','image'}
            if needed<=set(latest) and len(clocks)>2:break
        report['received']=list(latest)
        assert needed<=set(latest),'Missing TF/marker/rendered image'
        t=latest['tf'];p=t.transform.translation;q=t.transform.rotation
        actual=np.eye(4);actual[:3,:3]=Rotation.from_quat([q.x,q.y,q.z,q.w]).as_matrix();actual[:3,3]=[p.x,p.y,p.z]
        np.testing.assert_allclose(actual,expected,atol=1e-10)
        marker=next(m for m in latest['markers'].markers if m.mesh_resource)
        assert marker.mesh_use_embedded_materials and marker.mesh_resource==item['mesh_resource']
        assert [marker.scale.x,marker.scale.y,marker.scale.z]==[1,1,1]
        np.testing.assert_allclose([marker.pose.position.x,marker.pose.position.y,marker.pose.position.z],expected[:3,3],atol=1e-10)
        ok,scene=Transport().request('/world/uwa_lab/scene/info',Empty(),Empty,Scene,5000)
        assert ok,'No Gazebo scene'
        model=next(m for m in scene.model if m.name==item['model_name'])
        p=model.pose.position;q=model.pose.orientation
        gaz=np.eye(4);gaz[:3,:3]=Rotation.from_quat([q.x,q.y,q.z,q.w]).as_matrix();gaz[:3,3]=[p.x,p.y,p.z]
        np.testing.assert_allclose(gaz,expected,atol=1e-7)
        visual=next(v for link in model.link for v in link.visual)
        assert visual.geometry.mesh.filename.endswith('/carton.dae')
        report.update(T_world_object=expected.tolist(),gazebo_model_pose=gaz.tolist(),
            marker_resource=marker.mesh_resource,embedded_materials=True,
            clock_advance_s=clocks[-1]-clocks[0],visual_only=True,measured_world_accuracy_validated=False)
        assert report['clock_advance_s']>0
        if args.without_camera:
            report.update(success=True,rendered_camera_checked=False,
                camera_note='Sensor absent during parallel replay; preserved other job configuration')
            return
        image=latest['image'];channels=3
        bgr=np.frombuffer(image.data,np.uint8).reshape(image.height,image.step)[:,:image.width*channels].reshape(image.height,image.width,channels)
        if image.encoding=='rgb8':bgr=cv2.cvtColor(bgr,cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(out/'gazebo_overview.jpg'),cv2.resize(bgr,(1600,1200)))
        dimensions=np.array(item['manifest']['dimensions_m']);points=np.array([[x,y,z] for x in [0,dimensions[0]] for y in [0,dimensions[1]] for z in [0,dimensions[2]]])
        world=points@expected[:3,:3].T+expected[:3,3]
        cfg=camera_config(layout);camera=np.linalg.inv(transforms(cfg)[1]);local=world@camera[:3,:3].T+camera[:3,3]
        assert np.all(local[:,2]>0)
        pixels=cv2.projectPoints(local,np.zeros(3),np.zeros(3),intrinsic(cfg),np.zeros(5))[0].reshape(-1,2)
        low=np.maximum(0,np.floor(pixels.min(axis=0)-40).astype(int));high=np.minimum([image.width,image.height],np.ceil(pixels.max(axis=0)+40).astype(int))
        assert np.all(high>low),'Object outside simulated camera'
        crop=bgr[low[1]:high[1],low[0]:high[0]];cv2.imwrite(str(out/'gazebo_carton_crop.png'),crop)
        report.update(success=True,rendered_camera_checked=True,rendered_image_size=[image.width,image.height],
            crop_bounds=[low.tolist(),high.tolist()],clock_advance_s=clocks[-1]-clocks[0],
            visual_only=True,measured_world_accuracy_validated=False)
        assert report['clock_advance_s']>0
    except Exception as error:
        report['error']=str(error);raise
    finally:
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');node.destroy_node();rclpy.shutdown()
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
