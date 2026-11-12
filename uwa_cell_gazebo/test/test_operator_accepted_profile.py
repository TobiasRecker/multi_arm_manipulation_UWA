"""User acceptance never rewrites quality, defeats checksums, or admits bad geometry."""
import hashlib,json,shutil
from pathlib import Path
import numpy as np
import pytest
from uwa_cell_description.calibration_profile import load_profile,apply_layout
from uwa_cell_gazebo.configuration import nominal_layout_path,load_layout,render_description
from uwa_cell_gazebo.charuco_views import Chain


def source():
    return Path(__file__).resolve().parents[2]/'uwa_cell_description/config/calibration/hardware_20261112_v2'


def bundle(tmp_path):
    shutil.copytree(source(),tmp_path/'profile')
    return tmp_path/'profile/profile.json'


def test_explicit_adoption_retains_failure_metrics_and_matching_native_mode(tmp_path):
    profile=load_profile(source()/'profile.json');front=profile['robots']['right_front']
    assert not front['camera']['passed'] and not front['fit']['passed']
    assert set(front['quality_status'].values())=={'operator_accepted_below_threshold'}
    layout=apply_layout(load_layout(nominal_layout_path()),profile)
    assert [layout['robots']['right_front']['tools'][k] for k in ('camera_width','camera_height')]==[2592,1944]
    description=render_description(layout,tmp_path)[0]
    np.testing.assert_allclose(Chain(description,'right_front_tool0','right_front_wrist_camera_optical_frame').forward({}),front['fit']['T_tool0_camera'],atol=1e-12)
    old=load_profile(source().with_name('hardware_20261112_v1')/'profile.json')
    for rid in ('left_rear','right_rear'):
        for part in ('intrinsics','handeye','kinematics'):
            assert profile['robots'][rid][part]==old['robots'][rid][part]


@pytest.mark.parametrize('part',['intrinsics','handeye'])
def test_failed_quality_requires_exact_per_artifact_user_adoption(tmp_path,part):
    p=bundle(tmp_path);data=json.loads(p.read_text());del data['robots']['right_front']['operator_acceptance'][part];p.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='independent'):load_profile(p)


def test_acceptance_cannot_be_reused_for_other_bytes_or_unbounded_tool_offset(tmp_path):
    p=bundle(tmp_path);data=json.loads(p.read_text());front=data['robots']['right_front'];front['operator_acceptance']['handeye']['source_sha256']='0'*64;p.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='exact artifact'):load_profile(p)
    front['operator_acceptance']['handeye']['source_sha256']=front['handeye']['sha256']
    target=p.parent/front['handeye']['file'];fit=json.loads(target.read_text());fit['robots']['right_front']['T_tool0_camera'][0][3]=1.;target.write_text(json.dumps(fit));sha=hashlib.sha256(target.read_bytes()).hexdigest();front['handeye']['sha256']=sha;front['operator_acceptance']['handeye']['source_sha256']=sha;p.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='300mm'):load_profile(p)
