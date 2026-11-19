"""Reuse requires successful original registration and every unchanged input."""
import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from run_carton_cycle import reuse_registration
from uwa_cell_tasks.motion_review import digest


def fixture(tmp_path):
    src=tmp_path/'source';src.mkdir();image=tmp_path/'image.png';image.write_bytes(b'original capture')
    (src/'object-pose.json').write_text(json.dumps(dict(source_inputs={str(image):digest(image.read_bytes())})))
    (src/'registration.json').write_text(json.dumps(dict(success=True,object_pose=str(src/'object-pose.json'))))
    return src,image,tmp_path/'copy'


def test_exact_bound_capture_can_be_reused(tmp_path):
    src,image,dst=fixture(tmp_path);r=reuse_registration(src,dst,[image])
    assert r['sources_verified']==1 and (dst/'object-pose.json').read_bytes()==(src/'object-pose.json').read_bytes()


def test_changed_capture_is_not_reused(tmp_path):
    src,image,dst=fixture(tmp_path);image.write_bytes(b'new scene')
    with pytest.raises(ValueError,match='changed'):reuse_registration(src,dst,[image])
    assert not dst.exists()


def test_unbound_capture_is_not_reused(tmp_path):
    src,image,dst=fixture(tmp_path)
    with pytest.raises(ValueError,match='missing'):reuse_registration(src,dst,[tmp_path/'other.png'])


def test_failed_registration_is_not_reused(tmp_path):
    src,image,dst=fixture(tmp_path);(src/'registration.json').write_text('{"success":false}')
    with pytest.raises(ValueError,match='Successful'):reuse_registration(src,dst,[image])
