"""Exercise the actual HTTP adapter against a local camera server, never a UR."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

import pytest
from uwa_cell_control.wrist_camera import WristCamera, CameraError, save_snapshot


@pytest.fixture
def camera():
    state = {'focus': 100, 'focusAuto': True, 'lightingValue': 43, 'gain': 12}
    calls = []
    rejected = [False]

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            calls.append(('GET', self.path))
            self.send_response(200)
            self.end_headers()
            if self.path.startswith('/current.jpg'):
                self.wfile.write(b'\xff\xd8test-jpeg\xff\xd9')
            elif self.path.startswith('/triggerinprogress'):
                self.wfile.write(b'{"status":"succeeded","triggerInProgress":false}')
            else:
                self.wfile.write(json.dumps({'status': 'succeeded', 'cameraSettings': state}).encode())

        def do_POST(self):
            calls.append(('POST', self.path))
            raw = self.rfile.read(int(self.headers['Content-Length']))
            data = json.loads(raw) if raw else {}
            self.send_response(200)
            self.end_headers()
            if rejected[0]:
                self.wfile.write(b'{"status":"failed","error":"Camera busy"}')
            else:
                state.update(data.get('cameraSettings', {}))
                self.wfile.write(b'{"status":"succeeded"}')

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = WristCamera('127.0.0.1')
    client.base = f'http://127.0.0.1:{server.server_port}'
    yield client, state, calls, rejected
    server.shutdown()
    server.server_close()
    thread.join()


def test_focus_mapping_preserves_settings_and_restores_only_focus(camera):
    client, state, calls, _ = camera
    original = client.settings()
    result = client.manual(400)
    assert result['focus'] == 623 and result['focusAuto'] is False
    assert state['lightingValue'] == 43 and state['gain'] == 12
    state['lightingValue'] = 50  # Another user changed the light after our write.
    client.restore(original)
    assert state['focus'] == 100 and state['focusAuto'] is True
    assert state['lightingValue'] == 50
    assert all(path.startswith(('/getcamerasettings', '/setcamerasettings', '/trigger')) for _, path in calls)
    assert ('POST', '/trigger?focus=true&exposure=false&whiteBalance=false') in calls


def test_autofocus_enables_auto_and_triggers_focus_only(camera):
    client, state, calls, _ = camera
    state['focusAuto'] = False
    assert client.refocus()['focusAuto'] is True
    assert ('POST', '/trigger?focus=true&exposure=false&whiteBalance=false') in calls
    assert state['gain'] == 12 and state['lightingValue'] == 43


def test_rejection_and_invalid_values_do_not_claim_success(camera):
    client, state, calls, rejected = camera
    for invalid in (-1, 1024, True, 2.5):
        with pytest.raises(ValueError):
            client.manual(invalid)
    assert calls == []
    rejected[0] = True
    with pytest.raises(CameraError, match='Camera busy'):
        client.manual(512)
    assert state['focusAuto'] is True


def test_photo_has_receipt_timestamp_and_focus_metadata(camera, tmp_path):
    client, _, _, _ = camera
    path = save_snapshot(tmp_path, 'photo', client.image(), client.settings())
    metadata = json.loads(path.with_suffix('.json').read_text())
    assert path.read_bytes().startswith(b'\xff\xd8')
    assert metadata['settings']['focusAuto'] is True
    assert metadata['timestamp_kind'] == 'PC receipt; sensor exposure time unavailable'
    assert len(metadata['sha256']) == 64
