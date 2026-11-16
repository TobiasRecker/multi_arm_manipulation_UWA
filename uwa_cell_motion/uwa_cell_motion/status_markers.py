"""Independent interlock alerts; resource ownership is not a standstill proof."""
import math

from visualization_msgs.msg import Marker,MarkerArray


def interlock_markers(status,heartbeat_timeout):
    age=status.get('guard_age_s')
    lost=age is None or not math.isfinite(age) or age<0 or age>heartbeat_timeout
    blocked=set(status.get('blocked_arms',[]));held=set(status.get('held_arms',[]))
    markers=[Marker(action=Marker.DELETEALL)]
    if not lost and not blocked and not status.get('controller_error') and not status.get('monitor_only'):
        return MarkerArray(markers=markers),False
    alert=Marker();alert.header.frame_id='world';alert.ns='collision_interlock';alert.id=0
    alert.type=Marker.TEXT_VIEW_FACING;alert.pose.orientation.w=1.
    alert.pose.position.z=2.75;alert.scale.z=.09
    alert.color.r=alert.color.g=alert.color.b=alert.color.a=1.
    alert.lifetime.nanosec=350_000_000
    title='GUARD LOST' if lost else status.get('state','HOLD REQUESTED')
    # RViz's current text renderer gives spaces excessive width. Explicit
    # lines keep the critical state legible on the laboratory monitor.
    alert.text=title.replace(' ','\n')+f'\nHolds:{len(held&blocked)}/{len(blocked)}'
    if status.get('monitor_only'):
        alert.text='MONITOR\nONLY\nWould-stop:'+str(len(blocked))
        if lost:alert.text+='\nGUARD-LOST'
        markers.append(alert);return MarkerArray(markers=markers),lost
    if lost:alert.text+='\nStandstill:\nUNCONFIRMED'
    elif not status.get('interlock_confirmed',False):alert.text+='\nHOLD-PENDING'
    if status.get('controller_error'):alert.text+='\nCONTROLLER-ERROR'
    markers.append(alert)
    return MarkerArray(markers=markers),lost
