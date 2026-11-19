"""Partial visibility validates a frozen camera reference, never a new PnP fit."""
import sys
from pathlib import Path
import cv2,numpy as np,pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from register_carton_from_oak import validate_visible_board_projection


def fixture():
    obj=np.array([[x+dx,y+dy,0.]for x,y in [(0.,0.),(.12,0.),(0.,.12),(.12,.12)]for dx,dy in [(0.,0.),(.028,0.),(.028,.028),(0.,.028)]])
    T=np.eye(4);T[2,3]=1.;K=np.array([[1000.,0.,400.],[0.,1000.,300.],[0.,0.,1.]]);D=np.zeros(5)
    uv=cv2.projectPoints(obj,np.zeros(3),T[:3,3],K,D)[0].reshape(-1,2)
    return obj,uv,T,K,D


def test_current_markers_accept_unchanged_reference_without_mutation():
    obj,uv,T,K,D=fixture();old=T.copy();report=validate_visible_board_projection(obj,uv+.5,T,K,D)
    assert report['reference_projection_rms_px']==pytest.approx(np.sqrt(.5))
    np.testing.assert_array_equal(T,old)


def test_moved_camera_reference_or_bad_corner_cannot_pass():
    obj,uv,T,K,D=fixture()
    with pytest.raises(ValueError,match='disagrees'):validate_visible_board_projection(obj,uv+10.,T,K,D)
    uv[0,0]+=5.
    with pytest.raises(ValueError,match='disagrees'):validate_visible_board_projection(obj,uv,T,K,D)


def test_insufficient_or_narrow_marker_support_is_rejected():
    obj,uv,T,K,D=fixture()
    with pytest.raises(ValueError,match='distributed'):validate_visible_board_projection(obj[:12],uv[:12],T,K,D)
    obj[:,0]*=.01
    with pytest.raises(ValueError,match='distributed'):validate_visible_board_projection(obj,uv,T,K,D)
