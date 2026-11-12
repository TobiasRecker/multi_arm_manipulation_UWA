from copy import deepcopy
import numpy as np
import pytest
from uwa_cell_control.object_digitization import vertices,object_pose,project,solve,solid_parts


def data():
    parameters=np.array([.03,.04,.3,.53,.10,.10]);cameras={}
    for name,eye in [('a',[-.65,.3,-.75]),('b',[.9,-.25,-.55])]:
        eye=np.asarray(eye);z=np.array([.2,.1,0])-eye;z/=np.linalg.norm(z)
        x=np.cross(z,[0,1.,0]);x/=np.linalg.norm(x);y=np.cross(z,x)
        pose=np.eye(4);pose[:3,:3]=np.column_stack([x,y,z]);pose[:3,3]=eye
        cameras[name]={'T_camera_board':np.linalg.inv(pose).tolist(),
            'K':[[850.,0,640],[0,850.,480],[0,0,1]],'D':[0.]*5,
            'observation':{'image_size':[1280,960]},'board_rms_px':.2}
    observations={n:{'ids':list(range(8)),'pixels':project(vertices(parameters),c,1800).tolist()}
                  for n,c in cameras.items()}
    annotations={'proxy_width':1800,'metric_cameras':['a','b'],'observations':observations,
                 'assumed_wall_thickness_m':.0025}
    return parameters,cameras,annotations


def test_synthetic_unknown_box_dimensions_and_pose_recovered_from_images():
    expected,cameras,annotations=data();result=solve(cameras,annotations,sensitivity_draws=0)
    np.testing.assert_allclose(result['parameters_board_m_rad'],expected,atol=1e-7)
    assert result['depth_used'] is False and result['absolute_accuracy_validated'] is False
    assert not result['fit_independent_validation']


def test_annotation_outlier_does_not_determine_box_size():
    expected,cameras,annotations=data()
    annotations['observations']['a']['pixels'][4][0]+=40
    result=solve(cameras,annotations,sensitivity_draws=0)
    np.testing.assert_allclose(result['parameters_board_m_rad'][3:],expected[3:],atol=.006)


def test_missing_native_calibration_and_degenerate_views_are_rejected():
    _,cameras,annotations=data();del cameras['b']['K']
    with pytest.raises(ValueError,match='matching intrinsics'):solve(cameras,annotations,sensitivity_draws=0)
    _,cameras,annotations=data();cameras['b']=deepcopy(cameras['a'])
    with pytest.raises(ValueError,match='Degenerate views'):solve(cameras,annotations,sensitivity_draws=0)


def test_export_frame_is_rigid_right_handed_and_matches_fitted_vertices():
    parameters,_,_=data();pose=object_pose(parameters);points=vertices(parameters)
    np.testing.assert_allclose(pose[:3,:3].T@pose[:3,:3],np.eye(3),atol=1e-12)
    assert np.isclose(np.linalg.det(pose[:3,:3]),1.)
    L,W,H=parameters[3:]
    cad=np.array([[0,0,0],[L,0,0],[L,W,0],[0,W,0],[0,0,H]])
    projected=cad@pose[:3,:3].T+pose[:3,3]
    np.testing.assert_allclose(projected,points[[3,2,1,0,7]],atol=1e-12)


def test_open_tray_parts_have_no_overlapping_material_and_two_separate_dividers():
    result={'length_m':.53,'width_m':.10,'height_m':.10,'wall_thickness_m':.0025,
            'divider_fractions':[.328,.662]};parts=solid_parts(result)
    assert len(parts)==7
    for _,origin,size in parts:
        assert min(size)>0 and min(origin)>=0
        assert np.all(np.asarray(origin)+size<=np.array([.53,.10,.10])+1e-12)
    for i,(_,a,da) in enumerate(parts):
        for _,b,db in parts[i+1:]:
            intersection=np.minimum(np.asarray(a)+da,np.asarray(b)+db)-np.maximum(a,b)
            assert np.any(intersection<=1e-12)
