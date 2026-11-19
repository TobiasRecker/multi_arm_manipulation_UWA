"""Geometry marker rendering for the hardware guard."""
import time

import numpy as np
from geometry_msgs.msg import Point
from visualization_msgs.msg import Marker, MarkerArray


class CollisionGuard:
    def show(self, world, status):
        # Marker construction allocates hundreds of nested ROS messages. Keep
        # that display-only work out of headless supervision/benchmarks.
        if not self.markers.get_subscription_count():return
        if not status.get('stop_adapter_available',True):world={}
        markers=[Marker(action=Marker.DELETEALL)]; stamp=self.get_clock().now().to_msg(); number=0
        notice=Marker();notice.header.frame_id='world';notice.ns='model_uncertainty';notice.id=0;notice.type=Marker.TEXT_VIEW_FACING
        notice.pose.orientation.w=1.;notice.pose.position.z=2.4;notice.scale.z=.08
        notice.color.r=notice.color.g=notice.color.b=notice.color.a=1.
        notice.text=status.get('runtime_label','SIMULATION')+'\nWorld/table:provisional';markers.append(notice)
        for rid in self.names:
            if rid in world:continue
            label=Marker();label.header.frame_id=rid+'_base_link';label.ns='unknown';label.id=number;number+=1
            label.type=Marker.TEXT_VIEW_FACING;label.pose.orientation.w=1.;label.pose.position.z=.8;label.scale.z=.09
            label.color.r=label.color.g=label.color.b=label.color.a=1.;label.text=rid+'\n'+('STOP\nADAPTER\nLOST' if not status.get('stop_adapter_available',True) else 'STATE\nUNAVAILABLE')
            markers.append(label)
        for rid, centres in world.items():
            blocked=rid in status['blocked_arms'] or rid in self.supervisor_status.get('blocked_arms',[])
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
            if rid in status['blocked_arms']:state=status['state']
            elif blocked:
                state='STOPPED (HOLD)' if rid in self.supervisor_status.get('held_arms',[]) and self.core.stationary(rid,time.monotonic()) else 'STOPPING (HOLD)'
            else:state='CLEAR'
            record=self.core.records[rid];age=1000*(time.monotonic()-record['received'])
            source_age=1000*(status.get('source_time_s',self.get_clock().now().nanoseconds/1e9)-record['stamp'])
            label.text=rid+'\n'+state.replace(' ','\n')+f'\ndata:{age:.0f}ms/source:{source_age:.0f}ms'; markers.append(label)
        if status['state']!='CLEAR' or self.supervisor_status.get('blocked_arms'):
            alert=Marker();alert.header.frame_id='world';alert.ns='alert';alert.id=0;alert.type=Marker.TEXT_VIEW_FACING
            alert.pose.orientation.w=1.;alert.pose.position.z=2.2;alert.scale.z=.12
            alert.color.r=alert.color.g=alert.color.b=alert.color.a=1.
            state=status['state'] if status['state']!='CLEAR' else self.supervisor_status.get('state','HOLD')
            alert.text='COLLISION-GUARD:\n'+state.replace(' ','\n');markers.append(alert)
        for pair in self.pairs if status.get('stop_adapter_available',True) else []:
            line=Marker(); line.header.frame_id='world'; line.ns='nearest'; line.id=number; number+=1
            line.type=Marker.LINE_LIST; line.pose.orientation.w=1.; line.scale.x=.012
            line.color.r=line.color.g=line.color.a=1.
            line.points=[Point(x=p[0],y=p[1],z=p[2]) for p in pair['surface_points']]; markers.append(line)
            for p in pair['surface_points']:
                point=Marker();point.header.frame_id='world';point.ns='nearest_points';point.id=number;number+=1
                point.type=Marker.SPHERE;point.pose.orientation.w=1.;point.pose.position=Point(x=p[0],y=p[1],z=p[2])
                point.scale.x=point.scale.y=point.scale.z=.025;point.color.r=point.color.g=point.color.b=point.color.a=1.
                markers.append(point)
            label=Marker(); label.header.frame_id='world'; label.ns='distance'; label.id=number; number+=1
            label.type=Marker.TEXT_VIEW_FACING; label.pose.orientation.w=1.; label.scale.z=.045
            p=np.mean(pair['centres'],axis=0); label.pose.position=Point(x=float(p[0]),y=float(p[1]),z=float(p[2]+.08))
            label.color.r=label.color.g=label.color.b=label.color.a=1.
            label.text=f"{pair['clearance_m']*1000:.0f}mm\nSTOP:{pair['threshold_m']*1000:.0f}mm"
            if 'geometric_min_clearance_m' in pair:
                label.text='CRITICAL\n'+label.text+f"\nNearest:{pair['geometric_min_clearance_m']*1000:.0f}mm"
            markers.append(label)
        for marker in markers:marker.lifetime.nanosec=350_000_000
        self.markers.publish(MarkerArray(markers=markers))
