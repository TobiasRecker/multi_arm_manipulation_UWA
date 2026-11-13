"""Own static visual scene assets only; no controllers, hardware or arm actions."""
import fcntl
import os
from pathlib import Path
import time

from geometry_msgs.msg import TransformStamped
from gz.msgs.boolean_pb2 import Boolean
from gz.msgs.entity_factory_pb2 import EntityFactory
from gz.msgs.entity_pb2 import Entity
from gz.msgs.empty_pb2 import Empty
from gz.msgs.scene_pb2 import Scene
from gz.transport import Node as TransportNode
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from scipy.spatial.transform import Rotation
from std_srvs.srv import Trigger
from tf2_ros import StaticTransformBroadcaster
from visualization_msgs.msg import Marker, MarkerArray

from uwa_cell_description.configuration import default_layout_path, load_layout
from uwa_cell_description.scene_assets import instances, model_sdf


class SceneAssets(Node):
    def __init__(self):
        super().__init__('scene_assets',namespace='uwa_cell')
        self.declare_parameter('layout',str(default_layout_path()))
        self.transport=TransportNode();self.owned=set();self.current=[]
        self.markers=self.create_publisher(MarkerArray,'/uwa_cell/scene_assets/markers',
            QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.tf=StaticTransformBroadcaster(self)
        self.create_service(Trigger,'~/reload',self.reload)
        self.create_timer(2.,self.publish)
        deadline=time.monotonic()+60
        while rclpy.ok():
            try:self.apply();break
            except RuntimeError:
                if time.monotonic()>=deadline:raise
                time.sleep(1)

    def request(self,suffix,message,kind):
        ok,response=self.transport.request('/world/uwa_lab/'+suffix,message,kind,Boolean,3000)
        return ok and response.data

    def remove(self,name):
        return self.request('remove',Entity(name=name,type=Entity.MODEL),Entity)

    def apply(self):
        current=instances(load_layout(self.get_parameter('layout').value))
        # Resolve/validate every asset before modifying any displayed entity.
        descriptions=[(item,model_sdf(item)) for item in current]
        ok,scene=self.transport.request('/world/uwa_lab/scene/info',Empty(),Empty,Scene,3000)
        if not ok:raise RuntimeError('Gazebo scene unavailable')
        existing={model.name for model in scene.model}
        for item,sdf in descriptions:
            name=item['model_name']
            # Recover only our configured, namespaced models after an earlier
            # process crash; do not touch arbitrary Gazebo scene entities.
            if name in existing:
                if not self.remove(name):raise RuntimeError('Cannot replace scene asset '+name)
                self.owned.discard(name)
            if not self.request('create',EntityFactory(sdf=sdf,name=name,allow_renaming=False),EntityFactory):
                raise RuntimeError('Cannot create scene asset '+name)
            self.owned.add(name)
        desired={item['model_name'] for item in current}
        for name in self.owned-desired:
            if not self.remove(name):raise RuntimeError('Cannot remove old scene asset '+name)
        self.owned=desired;self.current=current
        frames=[]
        for item in current:
            pose=item['T_world_object'];msg=TransformStamped()
            msg.header.stamp=self.get_clock().now().to_msg();msg.header.frame_id='world';msg.child_frame_id=item['frame']
            msg.transform.translation.x,msg.transform.translation.y,msg.transform.translation.z=pose[:3,3].tolist()
            q=Rotation.from_matrix(pose[:3,:3]).as_quat().tolist()
            msg.transform.rotation.x,msg.transform.rotation.y,msg.transform.rotation.z,msg.transform.rotation.w=q
            frames.append(msg)
        if frames:self.tf.sendTransform(frames)
        self.publish();self.get_logger().info('VISUAL ASSETS LOADED: '+', '.join(item['id'] for item in current))

    def publish(self):
        clear=Marker(action=Marker.DELETEALL);clear.header.frame_id='world'
        message=MarkerArray(markers=[clear])
        for item in self.current:
            pose=item['T_world_object'];marker=Marker(ns='scene_assets',id=len(message.markers),type=Marker.MESH_RESOURCE)
            marker.header.frame_id='world';marker.pose.position.x,marker.pose.position.y,marker.pose.position.z=pose[:3,3].tolist()
            q=Rotation.from_matrix(pose[:3,:3]).as_quat().tolist()
            marker.pose.orientation.x,marker.pose.orientation.y,marker.pose.orientation.z,marker.pose.orientation.w=q
            marker.scale.x=marker.scale.y=marker.scale.z=1.
            marker.color.r=marker.color.g=marker.color.b=marker.color.a=1.
            marker.mesh_resource=item['mesh_resource'];marker.mesh_use_embedded_materials=True
            marker.lifetime.sec=6  # expire after a lost publisher; refreshed every2s
            message.markers.append(marker)
        self.markers.publish(message)

    def reload(self,request,response):
        try:self.apply();response.success=True;response.message='Visual assets reloaded; arm state unchanged.'
        except Exception as error:response.success=False;response.message=str(error)
        return response

    def close(self):
        self.current=[];self.publish()
        for name in list(self.owned):self.remove(name)


def main():
    if os.environ.get('ROS_DOMAIN_ID')!='64' or os.environ.get('GZ_PARTITION')!='uwa_cell_sim':
        raise RuntimeError('Use the cell env: domain64 / uwa_cell_sim')
    lock=Path(f'/tmp/uwa-scene-assets-{os.getuid()}-uwa_cell_sim.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        print('Scene assets are already managed in this cell.',flush=True);return
    rclpy.init();node=None
    try:node=SceneAssets();rclpy.spin(node)
    except (KeyboardInterrupt,ExternalShutdownException):pass
    finally:
        if node:
            if rclpy.ok():node.close()
            else:
                for name in list(node.owned):node.remove(name)
            node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        lock.close()


if __name__=='__main__':main()
