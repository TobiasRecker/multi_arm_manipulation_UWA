import json
import time
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from uwa_cell_gazebo.charuco import board_image
from uwa_cell_gazebo.configuration import load_layout
from uwa_cell_control.handeye_hardware import capture_observation


class Camera:
    def __init__(self,repeated=False):
        self.count=0;self.repeated=repeated
        self.data={'focus':404,'focusAuto':False,'exposureAuto':False,'exposure':60000,'gain':16}
        pattern=board_image(load_layout()['charuco'],'right')
        self.frame=cv2.resize(cv2.cvtColor(pattern,cv2.COLOR_GRAY2BGR),(560,400))
    def settings(self):return dict(self.data)
    def image(self):
        image=self.frame.copy()
        if not self.repeated:image[:8,:8]=self.count*35%255
        self.count+=1
        return cv2.imencode('.jpg',image)[1].tobytes()


class Observer:
    def __init__(self,moving=False):self.received={};self.count=0;self.moving=moving
    def sample(self,seconds):
        self.count+=1
        self.received={'right_rear':{'positions':[self.count*.01 if self.moving else 0.]*6,'received_monotonic':time.monotonic()}}
        return {r:dict(v) for r,v in self.received.items()}


DESCRIPTION='''<robot name="capture_test"><link name="right_rear_base_link"/>
<link name="right_rear_tool0"/><joint name="mount" type="fixed">
<parent link="right_rear_base_link"/><child link="right_rear_tool0"/>
<origin xyz="0 0 .5" rpy="0 0 0"/></joint></robot>'''


def test_stationary_capture_saves_raw_pixels_corners_and_explicit_timing_limit(tmp_path):
    record=capture_observation(Camera(),None,Observer(),SimpleNamespace(description=DESCRIPTION),
        load_layout(),'right_rear',tmp_path,'sample_000','fit')
    assert record['accepted'] and record['corners']==24
    assert record['freshness']['decoded_payload_changes']>=2
    assert not record['freshness']['sensor_exposure_timestamp_available']
    assert 'T_camera_board' not in record and 'camera_matrix' not in record
    assert (tmp_path/'sample_000.jpg').exists() and (tmp_path/'sample_000_annotated.jpg').exists()
    assert json.loads((tmp_path/'sample_000.json').read_text())['role']=='fit'
    with pytest.raises(ValueError,match='overwrite'):
        capture_observation(Camera(),None,Observer(),SimpleNamespace(description=DESCRIPTION),
            load_layout(),'right_rear',tmp_path,'sample_000','fit')


def test_repeated_pixels_motion_and_autofocus_do_not_create_accepted_measurement(tmp_path):
    for name,camera,observer,message in [('repeated',Camera(True),Observer(),'did not update'),
                                        ('moving',Camera(),Observer(True),'moved')]:
        with pytest.raises(ValueError,match=message):
            capture_observation(camera,None,observer,SimpleNamespace(description=DESCRIPTION),
                load_layout(),'right_rear',tmp_path,name,'fit',freshness_timeout=.03)
        assert not (tmp_path/(name+'.json')).exists()
    camera=Camera();camera.data['focusAuto']=True
    with pytest.raises(ValueError,match='fixed manual focus'):
        capture_observation(camera,None,Observer(),SimpleNamespace(description=DESCRIPTION),
            load_layout(),'right_rear',tmp_path,'auto','fit')
