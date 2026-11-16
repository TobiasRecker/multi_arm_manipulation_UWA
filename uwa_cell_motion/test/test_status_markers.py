from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]))

from visualization_msgs.msg import Marker
from uwa_cell_motion.status_markers import interlock_markers


def test_healthy_interlock_clears_previous_alarm():
    markers,lost=interlock_markers(dict(guard_age_s=.02,blocked_arms=[],held_arms=[],state='CLEAR'),.4)
    assert not lost and len(markers.markers)==1
    assert markers.markers[0].action==Marker.DELETEALL


def test_missing_guard_alarm_does_not_claim_standstill_from_resource_ownership():
    markers,lost=interlock_markers(dict(guard_age_s=.8,blocked_arms=['left_front'],held_arms=['left_front'],state='STOPPED',interlock_confirmed=True),.4)
    text=markers.markers[-1].text
    assert lost and 'GUARD\nLOST' in text and 'Holds:1/1' in text
    assert 'Standstill:\nUNCONFIRMED' in text and 'STOPPED' not in text
    assert markers.markers[-1].color.a==1. and markers.markers[-1].scale.z>=.09


def test_pending_resource_stop_remains_explicit():
    markers,lost=interlock_markers(dict(guard_age_s=.02,blocked_arms=['left_front','right_front'],held_arms=['left_front'],state='STOPPING',interlock_confirmed=False),.4)
    assert not lost and 'Holds:1/2' in markers.markers[-1].text
    assert 'HOLD-PENDING' in markers.markers[-1].text


def test_geometry_node_latches_missing_backend_without_reusing_old_clear_state():
    from types import SimpleNamespace
    from uwa_cell_motion.guard_node import CollisionGuard
    from uwa_cell_motion.common import ROBOT_IDS
    node=SimpleNamespace(model_match=True,supervisor_received=1.,cfg={'heartbeat_timeout_s':.4},core=SimpleNamespace())
    assert CollisionGuard.external_faults(node,1.2) and node.core.external_faults==[]
    assert not CollisionGuard.external_faults(node,1.5)
    assert node.core.external_faults==[dict(arms=list(ROBOT_IDS),reason='STOP ADAPTER LOST')]


def test_headless_guard_skips_all_display_work_when_nobody_subscribes():
    from types import SimpleNamespace
    from uwa_cell_motion.guard_node import CollisionGuard
    node=SimpleNamespace(markers=SimpleNamespace(get_subscription_count=lambda:0))
    # No clock/model/rendering state is touched by the unused display path.
    CollisionGuard.show(node,{}, {})
