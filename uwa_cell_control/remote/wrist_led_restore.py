"""Keep the leased LED state during native recovery. MIT."""
import os


def restore(function, worker, service, original):
    if os.environ.get('UWA_WRIST_MANAGED_LED') != '1':
        return function(service, original)
    request = worker.request
    def manual_request(path, data=None):
        if path.startswith('/setcamerasettings') and data and 'cameraSettings' in data:
            changes = dict(data['cameraSettings'])
            if 'lightingMode' in changes or 'lightingValue' in changes:
                # Translate the hardware switch to the setter enum. Preserve
                # explicit OFF even during a lease configured at zero.
                changes.update(lightingMode=1 if original['lightingMode'] == 0 else 2,
                               lightingValue=original['lightingValue'])
                data = {'cameraSettings': changes}
        return request(path, data)
    worker.request = manual_request
    try:
        result = function(service, original)
        result['managed_manual_led_restore'] = True
        return result
    finally:
        worker.request = request
