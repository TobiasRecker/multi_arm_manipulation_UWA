"""Independent task geometry process and the existing resource supervisor."""
import json
import tempfile
import time
import uuid
from pathlib import Path
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy
from std_msgs.msg import String
from std_srvs.srv import Trigger
from sensor_msgs.msg import JointState
from visualization_msgs.msg import MarkerArray
from uwa_cell_description.configuration import load_layout
from uwa_cell_motion.common import config as motion_config,guard_signature,ROBOT_IDS
from uwa_cell_motion.guard_core import GuardState
from uwa_cell_motion.geometry import SphereModel
from uwa_cell_calibration.model import CollisionModel
from uwa_cell_gazebo.charuco_views import Chain
from .core import ARMS,GraspGroup,verify
from .planning import actual_names
from .scene import apply_object,verify_scene


class TaskGuard(Node):
    def __init__(self,scene_directory,layout_file):
        super().__init__('collision_guard',namespace='/uwa_cell')
        self.set_parameters([rclpy.parameter.Parameter('use_sim_time',value=True)])
        self.directory=Path(scene_directory);self.scene=verify_scene(self.directory)
        self.description=(self.directory/'robot.urdf').read_text();self.layout=load_layout(layout_file)
        self.cfg=motion_config();self.names=actual_names(self.description,self.layout)
        self.temp=tempfile.TemporaryDirectory(prefix='uwa-task-guard-')
        self.model=SphereModel(self.description,self.names,self.cfg['sphere_spacing_m'])
        self.collision=CollisionModel(self.description,self.temp.name)
        self.core=GuardState(self.cfg);self.positions={};self.pairs=[]
        self.instance=str(uuid.uuid4());self.sequence=0;self.group=None;self.supervisor={}
        self.object=None;self.contacts=None;self.object_received=0.;self.contacts_received=0.
        self.runner_received=None;self.group_object=None;self.touching=False;self.releasing=False
        self.chains={a:Chain(self.description,'world',a+'_tool0') for a in ARMS}
        self.publisher=self.create_publisher(String,'~/decision',10)
        self.markers=self.create_publisher(MarkerArray,'tasks/markers',1)
        self.create_subscription(JointState,'/uwa_cell/joint_states',self.joints,qos_profile_sensor_data)
        self.create_subscription(String,'/uwa_cell/tasks/object_truth',self.object_message,10)
        self.create_subscription(String,'/uwa_cell/tasks/contacts',self.contact_message,10)
        self.create_subscription(String,'/uwa_cell/tasks/heartbeat',self.heartbeat,10)
        self.create_subscription(String,'/uwa_cell/tasks/group',self.membership,QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(String,'/uwa_cell/collision_supervisor/status',self.supervisor_message,10)
        self.create_service(Trigger,'~/reset',self.reset)
        self.wall=Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(.1,self.tick,clock=self.wall)

    def joints(self,msg):
        now=time.monotonic();stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9
        q=dict(zip(msg.name,msg.position));v=dict(zip(msg.name,msg.velocity))
        for a,names in self.names.items():
            if all(n in q and n in v for n in names):
                if self.core.receive(a,[q[n] for n in names],[v[n] for n in names],stamp,now):
                    self.positions.update({n:q[n] for n in names})

    def object_message(self,msg):self.object=json.loads(msg.data);self.object_received=time.monotonic()
    def contact_message(self,msg):self.contacts=json.loads(msg.data);self.contacts_received=time.monotonic()
    def heartbeat(self,msg):
        self.runner_received=time.monotonic()
        self.touching=json.loads(msg.data).get('phase') in ('grasp','form_group','move_object','set_down')
    def supervisor_message(self,msg):self.supervisor=json.loads(msg.data)

    def membership(self,msg):
        value=json.loads(msg.data)
        if value.get('released'):
            if self.contacts and self.contacts.get('supported') and all(self.core.stationary(a,time.monotonic()) for a in ARMS):
                self.group=None
            return
        if value.get('release_requested') and self.group and self.contacts and self.contacts.get('supported'):
            if all(a in self.core.records and max(abs(self.core.records[a]['v'][:6]))<.003 for a in ARMS):self.releasing=True
            return
        if self.group is not None:return  # offsets are immutable until supported release
        self.group=value

    def faults(self,now):
        faults=[]
        if self.runner_received is not None and now-self.runner_received>.5:
            faults.append(dict(arms=list(ARMS),reason='TASK RUNNER LOST'))
        if self.group:
            blocked=set(self.supervisor.get('blocked_arms',[]))|self.core.latched
            if blocked.intersection(ARMS):faults.append(dict(arms=list(ARMS),reason='GRASP GROUP MEMBER STOPPED'))
            if now-self.object_received>.2 or now-self.contacts_received>.2:
                faults.append(dict(arms=list(ARMS),reason='GRASP TELEMETRY STALE'))
            elif not all(all(self.contacts['pads'][a].values()) for a in ARMS) and not (self.releasing and self.contacts.get('supported')):
                faults.append(dict(arms=list(ARMS),reason='GRASP CONTACT LOST'))
            else:
                from match_cooperative_handling.rigid_object import pose_error
                obj=np.asarray(self.object['T_world_object'])
                for a in ARMS:
                    expected=obj@np.array(self.group['object_to_tcp'][a])
                    d,r=pose_error(self.chains[a].forward(self.positions),expected)
                    if d>self.scene['cfg']['relative_position_tolerance_m'] or r>self.scene['cfg']['relative_angle_tolerance_rad']:
                        faults.append(dict(arms=list(ARMS),reason='GRASP RIGIDITY ERROR / SLIP'))
                    region=self.group.get('contact_regions',{}).get(a)
                    if region and not self.releasing:
                        centre=np.array(region['point_object']);axis=np.array(region['normal_object'])
                        for side in ('left','right'):
                            valid=False
                            for contact in self.contacts['contacts']:
                                if not any(a+'_robotiq_85_'+side+'_finger_tip' in n for n in contact['collisions']):continue
                                for point,normal in zip(contact['positions'],contact.get('normals',[])):
                                    local=obj[:3,:3].T@(np.array(point)-obj[:3,3])
                                    local_normal=obj[:3,:3].T@np.array(normal)
                                    if np.linalg.norm(local-centre)<.04 and abs(local_normal@axis)>.7:valid=True
                            if not valid:faults.append(dict(arms=list(ARMS),reason='GRASP CONTACT OUTSIDE CHECKED WALL REGION'))
        return faults

    def tick(self):
        now=time.monotonic();source=self.get_clock().now().nanoseconds/1e9
        self.core.external_faults=self.faults(now)
        try:
            velocities={a:r['v'] for a,r in self.core.records.items()}
            ages={a:max(now-r['received'],source-r['stamp'],0.) for a,r in self.core.records.items()}
            _,self.pairs=self.model.pairs(self.positions,velocities,ages,self.cfg,partial=True)
            if len(self.core.records)==4 and self.object and now-self.object_received<.2:
                apply_object(self.collision,self.scene,self.object['T_world_object'],touching=bool(self.group) or self.touching)
                for table in ('left','right'):
                    self.collision.scene.allowed_collision_matrix.set_entry(table+'_table_plate',self.scene['object_id'],
                        bool(self.contacts and self.contacts.get('supported')))
                if not self.collision.check(self.positions)[0]:
                    self.core.external_faults.append(dict(arms=list(ARMS),reason='TASK FULL-SCENE COLLISION'))
        except Exception as error:
            self.pairs=[];self.core.external_faults.append(dict(arms=list(ROBOT_IDS),reason='GEOMETRY ERROR: '+str(error)))
        status=self.core.evaluate(self.pairs,now,source)
        # A fault in either member is immediately expanded, not on the next tick.
        if self.group and set(status['blocked_arms']).intersection(ARMS):
            self.core.latched.update(ARMS);status['blocked_arms']=sorted(self.core.latched)
        self.sequence+=1
        status.update(instance=self.instance,sequence=self.sequence,pairs=self.pairs,
            evaluated_monotonic_s=now,guard_config_signature=guard_signature(self.cfg),schema_version=1,
            source_time_s=source,scene_sha256=self.scene['sha256'])
        self.publisher.publish(String(data=json.dumps(status,allow_nan=False)))
        from .markers import object_markers
        self.markers.publish(object_markers(self,self.scene,self.object,status,self.group))

    def reset(self,req,res):
        if self.group:res.success=False;res.message='Loaded group cannot be reset automatically';return res
        self.runner_received=None
        self.core.external_faults=self.faults(time.monotonic())
        res.success,res.message=self.core.reset(self.pairs,time.monotonic(),self.get_clock().now().nanoseconds/1e9)
        return res


def supervisor_remaps(namespace):
    topics=['/clock','/uwa_cell/controller_manager/list_controllers','/uwa_cell/controller_manager/switch_controller',
        '/uwa_cell/collision_guard/reset','/uwa_cell/collision_guard/decision']
    for arm in ROBOT_IDS:
        for name in (arm+'_trajectory_controller',arm+'_gripper_controller'):
            topics.append('/uwa_cell/'+name+'/follow_joint_trajectory/_action/cancel_goal')
    return [(t,namespace+'/clock' if t=='/clock' else t.replace('/uwa_cell',namespace,1)) for t in topics]
