import json
import hashlib
import cv2
import numpy as np
import pytest
from uwa_cell_control.silhouette_mesh import mask_from_annotation, project, voxel_surface, reconstruct


def test_camera_from_board_projection_and_pixel_centres():
    c=dict(T_camera_board=np.array([[1,0,0,.2],[0,1,0,0],[0,0,1,2],[0,0,0,1]]).tolist(),
        K=[[100,0,50],[0,100,40],[0,0,1]],D=[0]*5,image_size=[100,80])
    xy,z=project(np.array([[0,0,0],[.2,0,0]]),c,50)
    np.testing.assert_allclose(xy,[[29.75,19.75],[34.75,19.75]])
    np.testing.assert_allclose(z,[2,2])


def test_mask_rotation_holes_and_bounds():
    item=dict(rotate_180=True,outer_polygon=[[1,1],[5,1],[5,6],[1,6]],holes=[[[2,2],[3,2],[3,3],[2,3]]])
    m=mask_from_annotation(item,10,10)
    assert m[8,8] and not m[7,7] and not m[0,0]
    with pytest.raises(ValueError):mask_from_annotation(dict(item,outer_polygon=[[-1,0],[1,0],[1,1]]),10,10)


def test_exposed_faces_have_outward_winding_and_metric_units():
    occ=np.ones((2,3,4),bool);v,f=voxel_surface(occ,[.2,.3,.4],.01)
    np.testing.assert_allclose(np.ptp(v,axis=0),[.02,.03,.04])
    volume=np.einsum('ij,ij->i',v[f[:,0]],np.cross(v[f[:,1]],v[f[:,2]])).sum()/6
    assert volume==pytest.approx(.02*.03*.04)
    assert len(f)==2*(2*3+2*4+3*4)*2


def synthetic(tmp_path, validation_extent):
    models={};views={};cube=np.array([[x,y,z] for x in [-.1,.1] for y in [-.1,.1] for z in [-.1,.1]])
    for i,centre in enumerate(([0,0,-2],[2,0,0],[0,2,0],[0,0,-2])):
        centre=np.array(centre,float);forward=-centre/np.linalg.norm(centre)
        up=np.array([0,1,0]) if abs(forward[1])<.9 else np.array([0,0,1])
        right=np.cross(up,forward);right/=np.linalg.norm(right)
        R=np.array([right,np.cross(forward,right),forward]);T=np.eye(4);T[:3,:3]=R;T[:3,3]=-R@centre
        image=tmp_path/f'{i}.png';cv2.imwrite(str(image),np.full((100,100,3),127,np.uint8))
        h=hashlib.sha256(image.read_bytes()).hexdigest()
        c=dict(T_camera_board=T.tolist(),K=[[100,0,50],[0,100,50],[0,0,1]],D=[0]*5,image_size=[100,100],
            image=str(image),image_sha256=h,metric_eligible=True,calibration_passed=True)
        xy,_=project(cube,c,100);poly=cv2.convexHull(xy.astype(np.float32)).reshape(-1,2).tolist()
        if i==3:poly=[[50-validation_extent,50-validation_extent],[50+validation_extent,50-validation_extent],
                     [50+validation_extent,50+validation_extent],[50-validation_extent,50+validation_extent]]
        models[str(i)]=c;views[str(i)]=dict(image_sha256=h,rotate_180=False,outer_polygon=poly,holes=[],role='fit' if i<3 else 'validation')
    m=tmp_path/'models.json';m.write_text(json.dumps(models));a=tmp_path/'annotations.json'
    a.write_text(json.dumps(dict(proxy_width=100,voxel_size_m=.02,mask_tolerance_px=0.,bounds_board_m=[[-.4]*3,[.4]*3],views=views)))
    return m,a


def test_independent_validation_never_changes_mesh(tmp_path):
    m,a=synthetic(tmp_path,2);reconstruct(m,a,tmp_path/'a')
    first=np.load(tmp_path/'a/mesh_board.npz')
    m,a=synthetic(tmp_path,12);reconstruct(m,a,tmp_path/'b')
    second=np.load(tmp_path/'b/mesh_board.npz')
    np.testing.assert_array_equal(first['vertices'],second['vertices'])
    np.testing.assert_array_equal(first['faces'],second['faces'])
    assert json.loads((tmp_path/'a/reconstruction.json').read_text())['geometry_validated'] is False


def test_metric_excluded_camera_and_changed_hash_rejected(tmp_path):
    m,a=synthetic(tmp_path,5);d=json.loads(m.read_text());d['0']['metric_eligible']=False;m.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='Metric-excluded'):reconstruct(m,a,tmp_path/'excluded')
    d['0']['metric_eligible']=True;d['0']['image_sha256']='bad';m.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='binding'):reconstruct(m,a,tmp_path/'hash')
