"""A colliding travel optimization must never replace a checked view route."""
import numpy as np
import pytest

from uwa_cell_calibration.planner import checked_view_order,nearest_checked_order
from uwa_cell_gazebo.configuration import joint_names


class Obstacle:
    def check(self,state):
        q=np.asarray([state[j] for j in joint_names('right_rear')])
        return (np.linalg.norm(q[:2]-[.5,.5])>.15,)


def examples():
    names=joint_names('right_rear');start=dict(zip(names,[0.]*6))
    poses=[dict(joints=[x,y,0.,0.,0.,0.],role='fit' if i<2 else 'validation')
           for i,(x,y) in enumerate([(1.,0.),(1.,1.),(0.,1.)])]
    return start,poses


def test_blocked_shortcut_falls_back_to_checked_order_and_preserves_roles():
    start,p=examples();model=Obstacle()
    result,reason=checked_view_order(model,'right_rear',start,[p[0],p[2],p[1]],p)
    assert result==p and 'rejected' in reason
    assert [v['role'] for v in result]==['fit','fit','validation']
    for pose in result:
        for point in pose['path']:
            assert model.check(dict(zip(joint_names('right_rear'),point['positions'])))[0]


def test_fallback_does_not_accept_an_original_route_with_a_collision():
    start,p=examples()
    with pytest.raises(ValueError,match='collision'):
        checked_view_order(Obstacle(),'right_rear',start,[p[0],p[2]], [p[0],p[2]])


def test_nearest_order_skips_blocked_candidate_and_keeps_every_view():
    start,p=examples();order=nearest_checked_order(Obstacle(),'right_rear',start,[p[0],p[2],p[1]])
    assert order==p
    for pose in order:
        for point in pose['path']:
            assert Obstacle().check(dict(zip(joint_names('right_rear'),point['positions'])))[0]
