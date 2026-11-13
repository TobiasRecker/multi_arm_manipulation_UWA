import json
from pathlib import Path
import shutil
import cv2
import numpy as np
import pytest

from uwa_cell_tracking.model import surface_reference
from uwa_cell_tracking.core import TexturePose
from uwa_cell_tracking.static import static_pose

ASSET=Path(__file__).resolve().parents[2]/'uwa_cell_description/assets/carton_avocado_v1'


def test_reference_does_not_use_saved_object_pose_and_rejects_modified_bank(tmp_path):
    cv2.setNumThreads(1);asset=tmp_path/'asset';shutil.copytree(ASSET,asset)
    first=tmp_path/'one.npz';surface_reference(asset,first,max_features=150)
    meta=json.loads((asset/'asset.json').read_text());meta['reference_pose']['T_frame_object']=[[999]*4]*4
    (asset/'asset.json').write_text(json.dumps(meta));second=tmp_path/'two.npz';surface_reference(asset,second,max_features=150)
    with np.load(first) as a,np.load(second) as b:
        np.testing.assert_array_equal(a['points'],b['points']);np.testing.assert_array_equal(a['descriptors'],b['descriptors'])
    assert not json.loads(first.with_suffix('.json').read_text())['reference_pose_used']
    with first.open('ab') as stream:stream.write(b'changed')
    with pytest.raises(ValueError,match='hash'):TexturePose(first)


def test_static_burst_rejects_duplicate_images_before_any_registration():
    class NoEstimator:
        def register(self,*args):raise AssertionError('Duplicate data must be rejected first')
    image=np.zeros((100,100,3),np.uint8)
    result=static_pose(NoEstimator(),[image,image.copy(),image.copy()],np.eye(3),np.zeros(5))
    assert result.status=='LOST' and result.T_camera_object is None
