"""Archive refuses altered image pixels, changed test roles and missing samples."""
import hashlib,json
import cv2
import numpy as np
import pytest
from uwa_cell_control.intrinsics_report import audit_records,finalize


def dataset(tmp_path):
    p=tmp_path/'records';p.mkdir()
    for i,role in enumerate(['fit','validation']):
        name=f'sample_{i:03d}';im=np.full((24,32,3),60+i*70,np.uint8)
        cv2.imwrite(str(p/(name+'.jpg')),im)
        pixels=cv2.imread(str(p/(name+'.jpg')))
        row=dict(sample_id=name,accepted=True,robot_id='right_rear',role=role,image=name+'.jpg',
            image_size=[32,24],pixel_sha256=hashlib.sha256(pixels.tobytes()).hexdigest(),
            T_base_tool0=np.eye(4).tolist(),capture_source=dict(kind='http_vga'))
        (p/(name+'.json')).write_text(json.dumps(row))
    return dict(arm='right_rear',segments=[dict(sample_id='sample_001',role='validation')])


def test_archive_audits_every_original_without_changing_it(tmp_path):
    batch=dataset(tmp_path);before={p:p.read_bytes() for p in (tmp_path/'records').iterdir()}
    rows,hashes=audit_records(tmp_path,batch)
    assert len(rows)==2 and len(hashes)==4
    assert all(p.read_bytes()==data for p,data in before.items())


@pytest.mark.parametrize('fault',['pixels','role','missing','native_provenance'])
def test_bad_archive_input_is_rejected(tmp_path,fault):
    batch=dataset(tmp_path);p=tmp_path/'records/sample_001.json';r=json.loads(p.read_text())
    if fault=='pixels':cv2.imwrite(str(tmp_path/'records/sample_001.jpg'),np.zeros((24,32,3),np.uint8))
    elif fault=='role':r['role']='fit';p.write_text(json.dumps(r))
    elif fault=='missing':p.unlink()
    else:r['capture_source']['kind']='wrist_hd_service';p.write_text(json.dumps(r))
    with pytest.raises(ValueError):audit_records(tmp_path,batch)


@pytest.mark.parametrize('passed',[True,False])
def test_export_preserves_quality_and_never_activates(tmp_path,passed):
    batch=dataset(tmp_path)
    for path,value in [('batch.json',batch),('session.json',{}),('operator_approval.json',{})]:
        (tmp_path/path).write_text(json.dumps(value))
    intrinsic=dict(passed=passed,fit_count=1,validation_count=1,focus=388,
        camera_matrix=[[30.,0.,16.],[0.,30.,12.],[0.,0.,1.]],
        distortion=[0.]*5,image_size=[32,24],fit_rms_px=.2,validation_rms_px=[.3])
    (tmp_path/'intrinsics.json').write_text(json.dumps(intrinsic))
    # These reduced synthetic observations test archive mechanics, not fitting.
    for path in (tmp_path/'records').glob('*.json'):
        row=json.loads(path.read_text());row['corners']=24;path.write_text(json.dumps(row))
    original=(tmp_path/'intrinsics.json').read_bytes();output=tmp_path/'result'
    if not passed:
        with pytest.raises(ValueError):finalize(tmp_path,tmp_path/'batch.json',output)
        assert not output.exists()
    else:
        report=finalize(tmp_path,tmp_path/'batch.json',output)
        assert report['passed'] and not report['activated'] and not report['handeye_fitted']
        assert (output/'intrinsics.json').read_bytes()==original
        assert (output/'camera_info.yaml').exists()
    assert (tmp_path/'intrinsics.json').read_bytes()==original
