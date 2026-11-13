"""Independent10Hz geometric decision process. No motion command clients."""
import json
import tempfile
import time
import uuid

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

from .common import ROBOT_IDS, all_names, model_context, simulation_only
from .geometry import SphereModel
from .guard_core import GuardState


class CollisionGuard(Node):
    def __init__(self, cfg, layout_path=None):
        super().__init__('collision_guard', namespace='/uwa_cell')
        self.set_parameters([rclpy.parameter.Parameter('use_sim_time', value=True)])
        self.directory = tempfile.TemporaryDirectory(prefix='uwa-guard-')
        self.layout, self.description, _ = model_context(self.directory.name, layout_path)
        self.names = all_names(self.layout)
        self.model = SphereModel(self.description, self.names, cfg['sphere_spacing_m'])
        self.core = GuardState(cfg); self.cfg = cfg; self.pairs = []; self.positions = {}
        self.instance = str(uuid.uuid4()); self.sequence = 0
        self.publisher = self.create_publisher(String, '~/decision', 10)
        self.markers = self.create_publisher(MarkerArray, '~/markers', 1)
        self.diagnostics = self.create_publisher(DiagnosticArray, '~/diagnostics', 10)
        self.create_subscription(JointState, '/uwa_cell/joint_states', self.receive, qos_profile_sensor_data)
        self.create_service(Trigger, '~/reset', self.reset)
        self.create_timer(1/cfg['rate_hz'], self.tick, clock=rclpy.clock.Clock())
        self.get_logger().info('RUNNING: four neighbor pairs,10Hz; reset is explicit; simulation only')

    def receive(self, msg):
        now = time.monotonic()
        stamp = msg.header.stamp.sec+msg.header.stamp.nanosec/1e9
        q = dict(zip(msg.name, msg.position)); v = dict(zip(msg.name, msg.velocity))
        for rid, names in self.names.items():
            if all(j in q and j in v for j in names):
                if self.core.receive(rid, [q[j] for j in names], [v[j] for j in names], stamp, now):
                    self.positions.update({j: q[j] for j in names})

    def geometry(self, now):
        velocities = {r: self.core.records[r]['v'] for r in self.names}
        ages = {r: max(0., now-self.core.records[r]['received']) for r in self.names}
        return self.model.pairs(self.positions, velocities, ages, self.cfg)

    def tick(self):
        now = time.monotonic(); world = None; error = None
        try:
            world, self.pairs = self.geometry(now)
        except Exception as e:
            self.pairs = []; error = str(e)
            self.core.latched.update(ROBOT_IDS)
        status = self.core.evaluate(self.pairs, now, self.get_clock().now().nanoseconds/1e9)
        if error: status.update(state='STATE STALE', geometry_error=error)
        self.sequence += 1
        status.update(instance=self.instance, sequence=self.sequence, pairs=self.pairs,
                      source_time_s=self.get_clock().now().nanoseconds/1e9,
                      state_ages_s={r: now-self.core.records[r]['received'] for r in self.core.records})
        self.publisher.publish(String(data=json.dumps(status, allow_nan=False)))
        diag = DiagnosticArray(); diag.header.stamp=self.get_clock().now().to_msg()
        item=DiagnosticStatus(name='Four-arm collision guard', hardware_id='SIMULATION',
            level=DiagnosticStatus.OK if status['state']=='CLEAR' else DiagnosticStatus.ERROR,
            message=status['state'], values=[KeyValue(key='blocked_arms',value=','.join(status['blocked_arms']))])
        diag.status=[item]; self.diagnostics.publish(diag)
        if world is not None: self.show(world, status)

    def show(self, world, status):
        markers=[]; stamp=self.get_clock().now().to_msg(); number=0
        for rid, centres in world.items():
            blocked=rid in status['blocked_arms']
            for centre, radius in zip(centres, self.model.radii[rid]):
                marker=Marker(); marker.header.frame_id='world'; marker.header.stamp=stamp
                marker.ns=rid; marker.id=number; number+=1; marker.type=Marker.SPHERE
                marker.pose.position=Point(x=float(centre[0]), y=float(centre[1]), z=float(centre[2]))
                marker.pose.orientation.w=1.; marker.scale.x=marker.scale.y=marker.scale.z=2*float(radius)
                marker.color.r=1. if blocked else .1; marker.color.g=.1 if blocked else .9
                marker.color.b=.1; marker.color.a=.32; markers.append(marker)
            label=Marker(); label.header.frame_id='world'; label.header.stamp=stamp
            label.ns='status'; label.id=number; number+=1; label.type=Marker.TEXT_VIEW_FACING
            label.pose.position=Point(x=float(centres[0,0]),y=float(centres[0,1]),z=1.7)
            label.pose.orientation.w=1.; label.scale.z=.10
            label.color.r=label.color.g=label.color.b=label.color.a=1.
            label.text=rid+' '+(status['state'] if blocked else 'CLEAR'); markers.append(label)
        for pair in self.pairs:
            line=Marker(); line.header.frame_id='world'; line.ns='nearest'; line.id=number; number+=1
            line.type=Marker.LINE_LIST; line.pose.orientation.w=1.; line.scale.x=.012
            line.color.r=line.color.g=line.color.a=1.
            line.points=[Point(x=p[0],y=p[1],z=p[2]) for p in pair['centres']]; markers.append(line)
            label=Marker(); label.header.frame_id='world'; label.ns='distance'; label.id=number; number+=1
            label.type=Marker.TEXT_VIEW_FACING; label.pose.orientation.w=1.; label.scale.z=.045
            p=np.mean(pair['centres'],axis=0); label.pose.position=Point(x=float(p[0]),y=float(p[1]),z=float(p[2]+.08))
            label.color.r=label.color.g=label.color.b=label.color.a=1.
            label.text=f"{pair['clearance_m']*1000:.0f}mm / STOP {pair['threshold_m']*1000:.0f}mm"; markers.append(label)
        self.markers.publish(MarkerArray(markers=markers))

    def reset(self, request, response):
        now=time.monotonic()
        try:
            _, pairs=self.geometry(now)
            response.success,response.message=self.core.reset(pairs,now,self.get_clock().now().nanoseconds/1e9)
        except Exception as error:
            response.success=False; response.message=str(error)
        return response


def run(cfg, layout=None):
    simulation_only(); rclpy.init(); node=CollisionGuard(cfg,layout)
    try:rclpy.spin(node)
    finally:node.destroy_node();rclpy.shutdown()
