"""Native-size, rollback and calibration source boundary regressions."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import time

import cv2
import numpy as np
import pytest

from uwa_cell_control.wrist_hd import SOURCE, validate_burst, make_camera
from uwa_cell_control.handeye_hardware import capture_observation
from uwa_cell_gazebo.configuration import load_layout
from uwa_cell_gazebo.charuco import board_image
from uwa_cell_control.hardware_charuco import calibrate_intrinsics


def test_native_focus_exposure_readback_rejects_wrong_or_missing_in_stream_controls():
    from uwa_cell_control.handeye_hardware import validate_native_controls
    settings=dict(focus=388,focusAuto=False,exposure=63410,exposureAuto=False,gain=19)
    samples=[dict(frame=i,focus_absolute=388,focus_auto=0,exposure_absolute=63410,exposure_auto=1,gain=19) for i in (3,5)]
    assert validate_native_controls(dict(sensor_controls=samples),settings)['passed']
    with pytest.raises(ValueError,match='both burst'):
        validate_native_controls(dict(sensor_controls=samples[:1]),settings)
    bad=[samples[0],dict(samples[1],focus_absolute=404)]
    with pytest.raises(ValueError,match='differs'):
        validate_native_controls(dict(sensor_controls=bad),settings)
    with pytest.raises(ValueError,match='differs'):
        validate_native_controls(dict(sensor_controls=[dict(s,exposure_auto=0) for s in samples]),settings)


def test_camera_key_reconnects_without_password_but_preserves_host_verification(tmp_path,monkeypatch):
    from uwa_cell_control.wrist_hd import SSH
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    client=SSH('192.168.8.103',tmp_path/'socket')
    assert '-i' not in client.base()
    key=tmp_path/'.ssh/uwa_wrist_camera_ed25519'
    key.parent.mkdir();key.write_text('test placeholder, not a private key')
    args=client.base()
    assert args[args.index('-i')+1]==str(key)
    assert all(option in args for option in ['IdentitiesOnly=yes','BatchMode=yes',
                                            'StrictHostKeyChecking=yes','ControlMaster=auto'])
    trusted=tmp_path/'.ssh/uwa_wrist_known_hosts'
    trusted.write_text('test host key placeholder')
    assert 'UserKnownHostsFile='+str(trusted) in client.base()
    legacy=tmp_path/'.ssh/uwa_wrist_camera_192_168_8_2_rsa'
    legacy.write_text('test placeholder, not a private key')
    old=SSH('192.168.8.2',tmp_path/'old_socket').base()
    assert old[old.index('-i')+1]==str(legacy)
    assert 'PubkeyAcceptedAlgorithms=+ssh-rsa' in old
    assert 'PubkeyAcceptedAlgorithms=+ssh-rsa' not in client.base()


def make_burst(path, size=(2592, 1944), restored=True, repeated=False):
    path.mkdir(exist_ok=True)
    for i in range(3):
        im = np.zeros((size[1], size[0], 3), np.uint8)
        im[:10, :10] = 80 if repeated else 40 + 60*i
        cv2.imwrite(str(path / f'frame_{i:03d}.jpg'), im)
    report = {'success': True, 'restore_ok': restored, 'transport': 'native_v4l2_mjpeg',
              'requested_size': [2592,1944], 'frames': [f'frame_{i:03d}.jpg' for i in range(3)]}
    (path/'report.json').write_text(json.dumps(report))


def test_burst_requires_native_pixels_changed_payloads_and_confirmed_restore(tmp_path):
    good=tmp_path/'good';make_burst(good)
    result=validate_burst(good,'192.168.8.103')
    assert result['image_size']==[2592,1944] and len(result['frames_metadata'])==3
    for name,kwargs,error in [('vga',{'size':(640,480)},'2592'),
                              ('bad_restore',{'restored':False},'restoration'),
                              ('cached',{'repeated':True},'did not change')]:
        p=tmp_path/name;make_burst(p,**kwargs)
        with pytest.raises(ValueError,match=error):validate_burst(p,'192.168.8.103')


def worker():
    path=Path(__file__).resolve().parents[1]/'remote/wrist_worker.py'
    spec=importlib.util.spec_from_file_location('remote_hd_worker_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_restore_waits_for_normal_and_uses_actual_readback_after_led_error(monkeypatch):
    m=worker();calls=[];phases=iter(['Initial','Normal'])
    original={'focus':435,'focusAuto':False,'exposure':60000,'exposureAuto':False,
              'gain':16,'lightingMode':0,'lightingValue':0}
    def request(path,data=None):
        calls.append(path)
        if path=='/status':return {'status':'succeeded','current state':next(phases)}
        if path.startswith('/set'):return {'status':'failed','code':15}
        return {'status':'succeeded','cameraSettings':dict(original)}
    monkeypatch.setattr(m,'request',request);monkeypatch.setattr(m.time,'sleep',lambda _:None)
    monkeypatch.setattr(m.subprocess,'check_call',lambda *a,**k:0)
    assert m.restore('/exact/camera/service',original)['all_original_fields_match']
    assert calls[:2]==['/status','/status']
    monkeypatch.setattr(m,'normal',lambda **k:None)
    monkeypatch.setattr(m,'settings',lambda:dict(original,focus=404))
    with pytest.raises(RuntimeError,match='readback mismatch'):m.restore('/exact/camera/service',original)


def test_native_failure_still_restores_camera_and_reports_failure(tmp_path,monkeypatch):
    m=worker();restored=[]
    monkeypatch.setattr(m,'normal',lambda **k:None)
    monkeypatch.setattr(m,'settings',lambda:{'focus':435})
    monkeypatch.setattr(m,'request',lambda *a,**k:{'status':'succeeded'})
    monkeypatch.setattr(m,'service_for_vision',lambda:('/only/vision/service',123))
    monkeypatch.setattr(m,'wait_vision_exit',lambda pid:None)
    monkeypatch.setattr(m.os,'fork',lambda:987654)
    monkeypatch.setattr(m.os,'waitpid',lambda *a:(987654,0))
    monkeypatch.setattr(m.os,'write',lambda *a:1)
    monkeypatch.setattr(m.subprocess,'check_call',lambda *a,**k:0)
    class Failed:
        pid=999999
        def __init__(self,args,stdout,stderr):stdout.write('Native capture failure\n')
        def wait(self):return 1
    monkeypatch.setattr(m.subprocess,'Popen',Failed)
    monkeypatch.setattr(m,'restore',lambda service,original:restored.append(service) or {'settings':original})
    result=m.capture(str(tmp_path/'request'))
    assert not result['success'] and result['restore_ok']
    assert restored==['/only/vision/service']


def test_restore_waits_for_async_settings_and_keeps_auto_mode_configuration_strict(monkeypatch):
    m=worker()
    original={'focus':388,'focusAuto':True,'exposure':33333,'exposureAuto':True,
              'gain':16,'lightingMode':0,'lightingValue':0,'focusWindowX1':165}
    monkeypatch.setattr(m,'normal',lambda **k:None)
    monkeypatch.setattr(m.subprocess,'check_call',lambda *a,**k:0)
    monkeypatch.setattr(m,'request',lambda *a,**k:{'status':'succeeded'})
    monkeypatch.setattr(m.time,'sleep',lambda _:None)
    states=iter([dict(original,lightingMode=1),dict(original,focus=700,exposure=10000,gain=32)])
    monkeypatch.setattr(m,'settings',lambda:next(states))
    result=m.restore('/only/camera/service',original)
    assert result['all_configuration_fields_match'] and not result['all_original_fields_match']
    assert result['automatic_output_fields']==['exposure','focus','gain']
    monkeypatch.setattr(m,'settings',lambda:dict(original,focusWindowX1=158))
    with pytest.raises(RuntimeError,match='focusWindowX1'):
        m.restore('/only/camera/service',original)


def test_restore_legacy_led_setter_mapping_requires_real_matching_readback(monkeypatch):
    m=worker()
    original={'focus':406,'focusAuto':False,'exposure':33333,'exposureAuto':False,
              'gain':16,'lightingMode':1,'lightingValue':0}
    actual=dict(original)
    def request(path,data=None):
        if path=='/hello':return {'version':'UCC-3.44.0.149696'}
        change=data['cameraSettings']
        if 'lightingMode' in change:actual['lightingMode']=1-change['lightingMode']
        return {'status':'succeeded'}
    monkeypatch.setattr(m,'normal',lambda **k:None)
    monkeypatch.setattr(m.subprocess,'check_call',lambda *a,**k:0)
    monkeypatch.setattr(m,'request',request)
    monkeypatch.setattr(m,'settings',lambda:dict(actual))
    monkeypatch.setattr(m.time,'sleep',lambda _:None)
    result=m.restore('/only/camera/service',original)
    assert result['all_original_fields_match'] and result['legacy_led_write_value']==0


def test_known_legacy_autofocus_roi_failure_declines_before_any_mode_change(tmp_path,monkeypatch):
    m=worker()
    monkeypatch.setattr(m,'normal',lambda **k:None)
    monkeypatch.setattr(m,'settings',lambda:{'focusAuto':True,'focus':388})
    monkeypatch.setattr(m,'request',lambda path:{'version':'UCC-1.11.1.10337'})
    def forbidden(*args,**kwargs):raise AssertionError('Must not stop service or change camera mode')
    monkeypatch.setattr(m,'service_for_vision',forbidden)
    monkeypatch.setattr(m.subprocess,'check_call',forbidden)
    result=m.capture(str(tmp_path/'request'))
    assert not result['success'] and result['restore_ok'] and not result['state_changed']
    assert 'autofocus ROI' in result['error']


@pytest.mark.parametrize('auto', [True, False])
def test_legacy_roi_feedback_restores_full_configuration_with_real_readback(monkeypatch, auto):
    m = worker()
    original = dict(focus=435, focusAuto=auto, exposure=60000, exposureAuto=False,
        gain=16, lightingMode=0, lightingValue=0, focusWindowX1=158,
        focusWindowY1=102, focusWindowX2=450, focusWindowY2=339)
    actual = dict(original, focusWindowX1=165, focusWindowY1=134)
    def request(path, data=None):
        if path == '/hello':
            return {'version': 'UCC-1.11.1.10337'}
        change = data['cameraSettings']
        if 'focusAuto' in change:
            actual['focusAuto'] = change['focusAuto']
            actual['lightingMode'] = 1
        for key, value in change.items():
            if key.startswith('focusWindow'):
                if actual['focusAuto']:
                    actual[key] = value - (16 if key == 'focusWindowY1' else 0)
            else:
                actual[key] = value
        if 'lightingMode' in change:
            actual['lightingMode'] = 1 - change['lightingMode']
        return {'status': 'succeeded'}
    monkeypatch.setattr(m, 'normal', lambda **k: None)
    monkeypatch.setattr(m.subprocess, 'check_call', lambda *a, **k: 0)
    monkeypatch.setattr(m, 'settings', lambda: dict(actual))
    monkeypatch.setattr(m, 'request', request)
    monkeypatch.setattr(m.time, 'sleep', lambda _: None)
    restored = m.restore('/camera/only', original)
    assert restored['all_configuration_fields_match']
    assert restored['settings'] == original and restored['legacy_roi_corrections']


def test_legacy_roi_feedback_cannot_accept_unbounded_or_ignored_coordinate_changes(monkeypatch):
    m = worker()
    original = dict(focus=435, focusAuto=True, exposure=60000, exposureAuto=False,
        gain=16, lightingMode=0, lightingValue=0, focusWindowX1=158,
        focusWindowY1=102, focusWindowX2=450, focusWindowY2=339)
    monkeypatch.setattr(m, 'normal', lambda **k: None)
    monkeypatch.setattr(m.subprocess, 'check_call', lambda *a, **k: 0)
    monkeypatch.setattr(m, 'settings', lambda: dict(original, focusWindowY1=300))
    monkeypatch.setattr(m, 'request', lambda *a, **k: {'version': 'UCC-1.11.1.10337'})
    monkeypatch.setattr(m.time, 'sleep', lambda _: None)
    with pytest.raises(RuntimeError, match='bounded range'):
        m.restore('/camera/only', original)


class BurstCamera:
    capture_source=SOURCE
    last_burst={'transport':'native_v4l2_mjpeg'}
    def settings(self):return {'focus':435,'focusAuto':False,'exposureAuto':False,'exposure':60000,'gain':16}
    def capture_burst(self,monitor):
        output=[]
        for i in range(3):
            monitor()
            im=cv2.cvtColor(board_image(load_layout()['charuco'],'right'),cv2.COLOR_GRAY2BGR)
            im[:8,:8]=30+i*40
            if i==2:im=cv2.GaussianBlur(im,(9,9),3)
            output.append(cv2.imencode('.jpg',im)[1].tobytes())
        return output


class Observer:
    def __init__(self):self.received={}
    def sample(self,timeout):
        self.received={'right_rear':{'positions':[0.]*6,'received_monotonic':time.monotonic()}}
        return self.received


DESCRIPTION='''<robot name="hd_test"><link name="right_rear_base_link"/>
<link name="right_rear_tool0"/><joint name="mount" type="fixed">
<parent link="right_rear_base_link"/><child link="right_rear_tool0"/></joint></robot>'''


def test_hd_observation_keeps_monitoring_and_selects_valid_sharp_frame(tmp_path):
    calls=[]
    r=capture_observation(BurstCamera(),None,Observer(),SimpleNamespace(description=DESCRIPTION),
        load_layout(),'right_rear',tmp_path,'sample_000','fit',capture_guard=lambda:calls.append(1))
    assert r['accepted'] and r['corners']==24 and r['capture_source']==SOURCE
    assert r['native_burst']['transport']=='native_v4l2_mjpeg'
    assert len(calls)>=3 and r['freshness']['decoded_payload_changes']==3
    assert not r['freshness']['sensor_exposure_timestamp_available']


def test_source_change_rejected_before_ros_or_fit():
    with pytest.raises(ValueError,match='Cannot change'):
        make_camera('192.168.8.103',None,SimpleNamespace(camera_source='wrist_hd_service'),
                    metadata={'capture_source':{'kind':'http_vga'}})
    records=[]
    for i in range(26):
        records.append({'role':'fit' if i<20 else 'validation','pixel_sha256':str(i),
                        'capture_source':SOURCE if i==0 else {'kind':'http_vga'}})
    with pytest.raises(ValueError,match='pipeline changed'):
        calibrate_intrinsics(records,focus=435,image_size=[2592,1944])


def test_hd_client_waits_for_service_restore_after_transient_motion(monkeypatch):
    import rclpy
    from uwa_cell_control.wrist_hd import HDCamera
    counter=[0]
    class Future:
        def done(self):return counter[0]>=5
        def result(self):return SimpleNamespace(success=True,message='{}')
    client=SimpleNamespace(wait_for_service=lambda **k:True,call_async=lambda req:Future())
    camera=HDCamera.__new__(HDCamera);camera.client=client;camera.node=None;camera.timeout=2
    monkeypatch.setattr(rclpy,'spin_once',lambda *a,**k:counter.__setitem__(0,counter[0]+1))
    def monitor():
        if counter[0]==2:raise ValueError('Robot moved during HD capture')
    with pytest.raises(ValueError,match='Robot moved'):
        camera.capture_burst(monitor)
    assert counter[0]==5  # Waited for transaction/restore, even after motion went away.


def test_service_discovery_uses_runsv_actual_cwd_and_checks_wrapper(monkeypatch):
    import io
    m=worker()
    files={'/proc/123/cmdline':b'./visionserver\0--portnum\04242\0',
           '/proc/123/stat':'123 (visionserver) S 234 0',
           '/proc/234/cmdline':b'/bin/bash\0/ur/camera/vision_server.sh\0',
           '/proc/234/stat':'234 (bash) S 345 0',
           '/proc/345/cmdline':b'runsv\0bundle@camera\0',
           '/ur/camera/service/run':'exec "/ur/camera/vision_server.sh"\n'}
    # Avoid octal escape ambiguity in the synthetic proc command line.
    files['/proc/123/cmdline']=b'./visionserver\0--portnum\0'+b'4242\0'
    def op(path,mode='r'):
        if path not in files:raise IOError(path)
        data=files[path]
        return io.BytesIO(data) if 'b' in mode else io.StringIO(data)
    monkeypatch.setattr(m,'open',op,raising=False)
    monkeypatch.setattr(m.glob,'glob',lambda pattern:['/proc/123'])
    monkeypatch.setattr(m.os,'readlink',lambda path:'/ur/camera/service')
    assert m.service_for_vision()==('/ur/camera/service',123)
    files['/ur/camera/service/run']='exec /ur/robot_control.sh\n'
    with pytest.raises(RuntimeError,match='Cannot uniquely'):m.service_for_vision()


def test_hd_fit_rejects_physical_camera_swap():
    records=[{'role':'fit' if i<20 else 'validation','pixel_sha256':str(i),
              'capture_source':SOURCE,'native_burst':{'camera':{'uniqueCamId':'A' if i<25 else 'B'}}}
             for i in range(26)]
    with pytest.raises(ValueError,match='identity changed'):
        calibrate_intrinsics(records,focus=435,image_size=[2592,1944])


def test_left_front_bootstrap_reuses_i686_helper_without_compiler(tmp_path):
    from uwa_cell_control.wrist_hd import LeftFrontNativeCapture
    class Remote:
        def __init__(self):self.calls=[]
        def run(self, command, **kwargs):self.calls.append((command,kwargs))
    remote=Remote(); capture=LeftFrontNativeCapture('192.168.8.2',remote,tmp_path)
    capture.bootstrap()
    commands=[command for command,_ in remote.calls]
    assert not any('gcc ' in command for command in commands)
    assert any('chmod 700 ' in command for command in commands)
    assert any(b'i686 Linux ABI' in call.get('data',b'') for _,call in remote.calls)
    assert capture.worker_entrypoint=='wrist_worker_fast.py'
    count=len(remote.calls);capture.bootstrap();assert len(remote.calls)==count
    with pytest.raises(ValueError):LeftFrontNativeCapture('192.168.8.170',remote,tmp_path)
