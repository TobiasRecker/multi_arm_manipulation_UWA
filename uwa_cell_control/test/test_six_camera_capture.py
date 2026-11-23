"""Six-source capture preserves raw USB pixels and reports shared-view pairs."""
import io
import json
import os
from types import SimpleNamespace

import cv2
import numpy as np

from uwa_cell_control.board_capture import SIX_CAMERAS
from uwa_cell_control.n100_usb_camera import N100UsbCamera
from test_board_capture import rig, config, board_image


def test_usb_failure_does_not_turn_five_successes_into_a_complete_set(tmp_path):
    r, _ = rig(tmp_path, failing='oak_usb')
    r.cameras, r.wrist_cameras = SIX_CAMERAS, SIX_CAMERAS[:4]
    r.usb = SimpleNamespace(focus=112)
    report = r.capture_all()
    assert len(report['cameras']) == 6 and not report['all_captured']
    assert report['cameras']['oak4']['success']
    assert not report['cameras']['oak_usb']['success']
    assert 'oak_usb' not in report['shared_board_cameras']


def test_both_external_leases_release_before_a_six_source_capture(tmp_path):
    r, calls = rig(tmp_path)
    r.cameras, r.wrist_cameras = SIX_CAMERAS, SIX_CAMERAS[:4]
    r.usb = SimpleNamespace(focus=112,stop=lambda:calls.append('usb-stop'),start=lambda:calls.append('usb-start'))
    r.previews = {'oak4':r.preview,'oak_usb':r.usb}
    def photo(name, directory, native):
        assert calls == ['stop','usb-stop']
        directory.mkdir()
        return dict(success=True,observation=dict(usable=name in ('left_front','oak_usb'),full=False,corners=16))
    r.capture_one = photo
    report = r.capture_all(resume_preview=True)
    assert report['all_captured'] and not report['all_usable']
    assert report['has_shared_board_pair']
    assert report['shared_board_pairs'] == [['left_front','oak_usb']]
    assert calls == ['stop','usb-stop','start','usb-start']


def test_usb_stream_rejects_truncated_payload_and_wrong_identity(tmp_path):
    camera = N100UsbCamera(tmp_path,tmp_path/'preview')
    header = dict(bytes=5,device_id=camera.device_id,lens_position=112,received=0)
    camera._receive(SimpleNamespace(stdout=io.BytesIO(b'UWA_FRAME '+json.dumps(header).encode()+b'\nabc')))
    assert 'Incomplete' in camera.error and camera.latest is None
    camera.error = None
    header['device_id'] = 'other-camera'
    camera._receive(SimpleNamespace(stdout=io.BytesIO(b'UWA_FRAME '+json.dumps(header).encode()+b'\nabcde')))
    assert 'identity' in camera.error and camera.latest is None


def test_different_static_boards_never_form_a_shared_calibration_pair(tmp_path):
    r, _ = rig(tmp_path)
    r.cameras, r.wrist_cameras = SIX_CAMERAS, SIX_CAMERAS[:4]
    r.usb = SimpleNamespace(focus=112)
    def photo(name,directory,native):
        directory.mkdir()
        return dict(success=True,observation=dict(usable=name in ('left_front','oak_usb'),
            full=False,corners=16,board_id=name+'_different_board'))
    r.capture_one=photo
    report=r.capture_all()
    assert report['all_captured'] and not report['has_shared_board_pair']
    assert not report['shared_board_pairs']


def test_six_source_gui_rotates_only_usb_display_and_accepts_pair_views(tmp_path,monkeypatch):
    os.environ['QT_QPA_PLATFORM']='offscreen'
    from python_qt_binding import QtWidgets
    from uwa_cell_control.board_capture_gui import Window,Worker
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(Worker,'start',lambda _:None)
    window = Window(SimpleNamespace(cameras=SIX_CAMERAS,board_config=config(),session=tmp_path))
    assert len(window.labels)==6 and window.capture.text()=='CAPTURE ALL SIX'
    assert '4056' in window.mode.itemText(0)
    frame = board_image()
    jpeg=cv2.imencode('.jpg',frame)[1].tobytes()
    original=cv2.imdecode(np.frombuffer(jpeg,np.uint8),cv2.IMREAD_COLOR)
    received=[]
    window.worker.frame.connect(lambda name,data,meta:received.append((data,meta)))
    window.worker.publish('oak_usb',jpeg,{'received':0,'kind':'SAVED SNAPSHOT'})
    assert received[0][1]['display_rotation_deg']==180
    np.testing.assert_array_equal(cv2.imdecode(np.frombuffer(jpeg,np.uint8),cv2.IMREAD_COLOR),original)
    window.on_result(dict(directory=str(tmp_path),all_captured=True,all_usable=False,
        has_shared_board_pair=True,shared_board_cameras=['left_front','oak_usb'],stationary_set_confirmed=True,
        cameras={n:dict(success=True,observation=dict(corners=16 if n in ('left_front','oak_usb') else 0)) for n in SIX_CAMERAS}))
    assert '1 usable sets' in window.totals.text()
    assert window.capture_state.text().startswith('DONE')
    window.close();app.processEvents()
