"""Small nonblocking client shared by the Qt UI and unattended verification."""
import json,uuid,time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy,qos_profile_sensor_data
from std_msgs.msg import String
from std_srvs.srv import Trigger
from sensor_msgs.msg import Image
from uwa_cell_calibration_msgs.srv import PrepareCalibration,ApplyCalibration
from uwa_cell_calibration_msgs.action import RunCalibration
from uwa_cell_gazebo.configuration import ROBOT_IDS

PREFIX='/uwa_cell/calibration'

class Client(Node):
    def __init__(self):
        super().__init__('calibration_client_'+uuid.uuid4().hex[:8])
        self.client_id=uuid.uuid4().hex
        self.state={};self.images={};self.goal=None;self.result=None;self.error=''
        self.last_status=0.;self.last_pulse=time.monotonic()
        qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(String,PREFIX+'/status',self.on_status,qos)
        self.heartbeat=self.create_publisher(String,PREFIX+'/heartbeat',10)
        self.create_timer(.2,self.send_heartbeat)
        for rid in ROBOT_IDS:
            self.create_subscription(Image,f'{PREFIX}/{rid}/image_annotated',lambda m,r=rid:self.images.update({r:m}),qos_profile_sensor_data)
        self.prepare_client=self.create_client(PrepareCalibration,PREFIX+'/prepare')
        self.apply_client=self.create_client(ApplyCalibration,PREFIX+'/apply')
        self.commands={c:self.create_client(Trigger,PREFIX+'/'+c) for c in ('pause','resume','stop','pause_world')}
        self.action=ActionClient(self,RunCalibration,PREFIX+'/run')

    def on_status(self,msg):
        try:self.state=json.loads(msg.data);self.last_status=time.monotonic()
        except (TypeError,ValueError):pass

    def pulse(self):self.last_pulse=time.monotonic()

    def send_heartbeat(self):
        # A responsive ROS thread alone must not keep a frozen GUI alive.
        if time.monotonic()-self.last_pulse<.5:
            self.heartbeat.publish(String(data=self.client_id))

    def service(self,client,request):
        if not client.service_is_ready():self.error='Kalibrierungsbackend nicht erreichbar';return None
        future=client.call_async(request)
        def done(f):
            try:
                response=f.result()
                if not getattr(response,'accepted',getattr(response,'success',False)):self.error=response.message
            except Exception as error:self.error=str(error)
        future.add_done_callback(done);return future

    def prepare(self,robots,count):
        self.error='';self.result=None
        return self.service(self.prepare_client,PrepareCalibration.Request(robot_ids=robots,samples_per_robot=count,client_id=self.client_id))

    def command(self,name):return self.service(self.commands[name],Trigger.Request())

    def start(self):
        if not self.action.server_is_ready():self.error='Session action nicht erreichbar';return
        future=self.action.send_goal_async(RunCalibration.Goal(plan_id=self.state.get('plan_id','')))
        def accepted(f):
            try:
                self.goal=f.result()
                if not self.goal.accepted:self.error='Start wurde abgelehnt; Posen erneut vorbereiten';return
                result=self.goal.get_result_async()
                result.add_done_callback(lambda f:setattr(self,'result',f.result().result))
            except Exception as error:self.error=str(error)
        future.add_done_callback(accepted)

    def apply(self):
        return self.service(self.apply_client,ApplyCalibration.Request(result_path=self.state.get('result_path',''),client_id=self.client_id))
