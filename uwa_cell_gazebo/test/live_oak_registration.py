"""Read-only acceptance of the installed overview in simulation domain64."""
import json
from pathlib import Path
import time

import cv2
import numpy as np
import rclpy
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image, CameraInfo, JointState
from tf2_msgs.msg import TFMessage
from visualization_msgs.msg import MarkerArray
from controller_manager_msgs.srv import ListControllers
from scipy.spatial.transform import Rotation
from gz.transport import Node as Transport
from gz.msgs.empty_pb2 import Empty
from gz.msgs.scene_pb2 import Scene

from uwa_cell_gazebo.configuration import load_layout
from uwa_cell_gazebo.overview import camera_config, transforms, intrinsic, MODEL, FRAME, TOPIC


def main():
    output=Path.home()/'UWA_ws/setup/calibration/three_camera_evaluation_20261112/adoption-live'
    output.mkdir(exist_ok=True)
    layout=load_layout();cfg=camera_config(layout)
    rclpy.init();node=rclpy.create_node('uwa_oak_registration_check')
    latest={};frames=[];times=[];static={}
    qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)
    def image(msg):
        latest['image']=msg
        frames.append((msg.header.stamp.sec,msg.header.stamp.nanosec))
    def clock(msg):times.append(msg.clock.sec+msg.clock.nanosec*1e-9)
    def tf(msg):
        for t in msg.transforms:static[t.child_frame_id]=t
    subscriptions=[node.create_subscription(Image,TOPIC+'/image_raw',image,qos_profile_sensor_data),
        node.create_subscription(CameraInfo,TOPIC+'/camera_info',lambda m:latest.update(info=m),qos_profile_sensor_data),
        node.create_subscription(TFMessage,'/tf_static',tf,qos),
        node.create_subscription(Clock,'/clock',clock,qos_profile_sensor_data),
        node.create_subscription(JointState,'/uwa_cell/joint_states',lambda m:latest.update(joints=m),qos_profile_sensor_data),
        node.create_subscription(MarkerArray,'/uwa_cell/oak_overview/markers',lambda m:latest.update(markers=m),qos)]
    client=node.create_client(ListControllers,'/uwa_cell/controller_manager/list_controllers')
    future=None;controllers={};deadline=time.monotonic()+45
    try:
        while time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.1)
            if future is None and client.service_is_ready():future=client.call_async(ListControllers.Request())
            if future and future.done():
                controllers={c.name:c.state for c in future.result().controller};future=None
            if (set(latest)=={'image','info','joints','markers'} and len(set(frames))>=2
                    and len(times)>2 and FRAME in static and cfg['real_frame_id'] in static
                    and len(controllers)==9 and all(v=='active' for v in controllers.values())):break
        report=dict(profile=layout['calibration']['profile_id'],success=False,controllers=controllers,
            rendering_model=cfg.get('rendering_model','nominal'),
            received=list(latest),distinct_images=len(set(frames)),clock_advance_s=times[-1]-times[0] if len(times)>1 else 0)
        assert {'image','info','joints','markers'}<=set(latest),'Missing live ROS outputs'
        info=latest['info'];im=latest['image']
        report.update(size=[im.width,im.height],frame=im.header.frame_id,K=list(info.k),D=list(info.d))
        assert im.header.frame_id==info.header.frame_id==FRAME
        assert [im.width,im.height]==[cfg['width'],cfg['height']]
        np.testing.assert_allclose(np.asarray(info.k).reshape(3,3),intrinsic(cfg),atol=1e-5)
        np.testing.assert_allclose(info.d,cfg['distortion'],atol=1e-6)
        report['transforms']={}
        for name in (FRAME,cfg['real_frame_id']):
            t=static[name];q=t.transform.rotation;p=t.transform.translation
            matrix=np.eye(4);matrix[:3,:3]=Rotation.from_quat([q.x,q.y,q.z,q.w]).as_matrix();matrix[:3,3]=[p.x,p.y,p.z]
            assert t.header.frame_id=='world'
            np.testing.assert_allclose(matrix,transforms(cfg)[1],atol=1e-10)
            report['transforms'][name]=matrix.tolist()
        assert np.isfinite(latest['joints'].position).all()
        assert report['clock_advance_s']>0 and len(set(frames))>=2
        assert len(controllers)==9 and all(v=='active' for v in controllers.values())
        report['markers_text']=[m.text for m in latest['markers'].markers if m.text]
        assert any('PRELIMINARY' in text for text in report['markers_text'])
        report['rviz_subscriptions']=[dict(node=s.node_name,namespace=s.node_namespace) for s in
            node.get_subscriptions_info_by_topic('/uwa_cell/oak_overview/markers')]
        assert any('rviz' in s['node'] for s in report['rviz_subscriptions'])
        bgr=np.frombuffer(im.data,np.uint8).reshape(im.height,im.step)[:,:im.width*3].reshape(im.height,im.width,3)
        if im.encoding=='rgb8':bgr=cv2.cvtColor(bgr,cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(output/'simulated-overview.jpg'),cv2.resize(bgr,(1200,900)))
        transport=Transport();ok,scene=transport.request('/world/uwa_lab/scene/info',Empty(),Empty,Scene,4000)
        assert ok,'Gazebo scene unavailable'
        model=next(m for m in scene.model if m.name==MODEL)
        link=next(l for l in model.link if l.name=='rgb_camera')
        p=link.pose.position;q=link.pose.orientation
        actual=np.eye(4);actual[:3,:3]=Rotation.from_quat([q.x,q.y,q.z,q.w]).as_matrix();actual[:3,3]=[p.x,p.y,p.z]
        np.testing.assert_allclose(actual,transforms(cfg)[0],atol=1e-7)
        report['gazebo_sensor_link_pose']=actual.tolist()
        report['success']=True
    except Exception as error:
        report=locals().get('report',dict(profile=layout['calibration']['profile_id'],success=False))
        report['error']=str(error)
        raise
    finally:
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        node.destroy_node();rclpy.shutdown()
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
