import numpy as np
import pytest

from uwa_cell_tasks.workpiece_paths import AxialFeed, SurfaceFrame, SurfacePolyline


def test_axial_feed_on_tilted_surface_keeps_tool_axis_and_returns_to_clearance():
    normal = np.array([0., .6, .8])
    frame = SurfaceFrame((.1, .2, .3), normal, (1., 0., 0.))
    poses = AxialFeed((.03, -.02), .04, .008).reference(frame)
    entry = poses['surface']
    assert np.allclose(entry[:3, 3], np.array([.13, .184, .312]))
    assert np.allclose(poses['approach'][:3, 3] - entry[:3, 3], .04 * normal)
    assert np.allclose(poses['depth'][:3, 3] - entry[:3, 3], -.008 * normal)
    assert np.array_equal(poses['withdrawn'], poses['approach'])
    for pose in poses.values():
        assert np.allclose(pose[:3, 2], -normal)
        assert np.linalg.det(pose[:3, :3]) == pytest.approx(1.)


def test_path_contract_rejects_inconsistent_frame_and_degenerate_work_stroke():
    with pytest.raises(ValueError, match='orthogonal unit vectors'):
        SurfaceFrame((0, 0, 0), (0, 0, 1), (0, 0, 1))
    with pytest.raises(ValueError, match='nonzero consecutive edges'):
        SurfacePolyline(((0., 0.), (.02, .01), (.02, .01)))
    with pytest.raises(ValueError, match='positive and finite'):
        AxialFeed((0., 0.), .04, -.001)
