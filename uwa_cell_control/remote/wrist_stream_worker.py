"""One bounded native-camera lease with independent restore on client loss (Python 2.7/3)."""
from __future__ import print_function
import errno
import fcntl
import json
import os
import select
import subprocess
import sys
import time

import wrist_led_restore
import wrist_stream_v4l2 as v4l2
import wrist_worker as vision


def send(header, payload=b''):
    header['bytes'] = len(payload)
    packet = (json.dumps(header, separators=(',', ':')) + '\n').encode('ascii') + payload
    position = 0
    deadline = time.time() + 8
    while position < len(packet):
        if not select.select([], [1], [], max(0, deadline - time.time()))[1]:
            raise RuntimeError('Wrist client stopped receiving')
        # A single, large blocking write could outlive the lease on a dead link.
        size = os.write(1, packet[position:position+4096])
        if not size:
            raise RuntimeError('Wrist client disconnected')
        position += size


def restore_camera(service, settings, original_mode):
    result = wrist_led_restore.restore(vision.restore_settings, vision, service, settings)
    try:
        result['mode'] = v4l2.check_mode(original_mode)
    except Exception:
        current_service, pid = vision.service_for_vision()
        if current_service != service:
            raise RuntimeError('Camera service identity changed during restoration')
        subprocess.check_call(['sv', 'down', service], stdout=subprocess.PIPE)
        try:
            vision.wait_vision_exit(pid)
            v4l2.check_mode(original_mode, apply=True)
        finally:
            result = wrist_led_restore.restore(vision.restore_settings, vision, service, settings)
        result['mode'] = v4l2.check_mode(original_mode)
    return result


def restoration_watchdog(directory, service, settings, original_mode):
    """Child inherits the exclusive lock, stays alive if the SSH worker dies."""
    reader, writer = os.pipe()
    pid = os.fork()
    if pid:
        os.close(reader)
        return pid, writer
    try:
        os.close(writer)
        os.setsid()
        nullfd = os.open(os.devnull, os.O_RDWR)
        for stdio in (0, 1, 2):
            os.dup2(nullfd, stdio)
        os.close(nullfd)
        os.read(reader, 1)  # EOF only after acquisition releases its camera descriptor.
        for attempt in range(2):
            try:
                restored = restore_camera(service, settings, original_mode)
                result = dict(restore_ok=True, restoration=restored)
                break
            except Exception as error:
                result = dict(restore_ok=False, error=str(error))
        report = os.path.join(directory, 'restoration.json')
        vision.save(report+'.tmp', result)
        os.rename(report+'.tmp', report)
    finally:
        os._exit(0)


def checked_controls(camera, focus):
    values = v4l2.sensor_controls(camera.fd)
    if values.get('focus_auto') != 0 or values.get('focus_absolute') != focus:
        raise RuntimeError('Native sensor readback differs from the fixed session focus')
    return values


def stream(camera, identity, settings, focus):
    warmed = 0
    pending = None
    skip = 0
    deadline = time.time() + 5
    while True:
        ready = select.select([0, camera.fd], [], [], max(0, min(2., deadline-time.time())))[0]
        if time.time() >= deadline:
            raise RuntimeError('Wrist session client or native frame timed out')
        if 0 in ready:
            # The host serializes requests and sends a single byte per command.
            command = os.read(0, 1)
            if command in (b'', b'X'):
                return
            if command == b'P':
                send(dict(event='pong'))
                deadline = time.time() + 24
            elif command in (b'V', b'C') and warmed >= 3 and pending is None:
                pending = command
                # Up to four buffers may already have reached the driver when the
                # request arrives. Drain those, then skip one in-progress frame.
                for _ in range(len(camera.maps)):
                    if not select.select([camera.fd], [], [], 0)[0]:
                        break
                    camera.dequeue(False)
                skip = 1
                deadline = time.time() + 3
            else:
                raise RuntimeError('Invalid wrist frame protocol state')
        if camera.fd in ready:
            acquired = camera.dequeue(pending is not None and skip == 0)
            if acquired is None:
                continue
            meta, jpeg = acquired
            if warmed < 3:
                warmed += 1
                if warmed == 3:
                    send(dict(event='ready', camera_identity=identity, settings=settings,
                              controls=checked_controls(camera, focus), image_size=list(v4l2.SIZE)))
                    deadline = time.time()+24
            elif pending is not None:
                if skip:
                    skip -= 1
                else:
                    meta.update(event='frame', sensor_controls=checked_controls(camera, focus))
                    send(meta, jpeg)
                    pending = None
                    deadline = time.time()+24


def acquire(directory, focus, identity, settings, service, pid):
    fd = v4l2.device()
    try:
        original_mode = v4l2.mode(fd)
    finally:
        os.close(fd)
    vision.save(os.path.join(directory, 'original.json'), dict(
        camera_identity=identity, original_settings=settings, mode=v4l2.saveable(original_mode)))
    watch, release = restoration_watchdog(directory, service, settings, original_mode)
    error = None
    try:
        subprocess.check_call(['sv', 'down', service], stdout=subprocess.PIPE)
        vision.wait_vision_exit(pid)
        for attempt in range(20):
            camera = v4l2.Camera()
            try:
                try:
                    camera.start()
                except IOError as start_error:
                    if attempt < 19 and start_error.errno in (errno.EBUSY, errno.EIO):
                        time.sleep(.25)
                        continue
                    raise
                stream(camera, identity, settings, focus)
                break
            finally:
                camera.close()
    except BaseException as failure:
        error = str(failure) or type(failure).__name__
    finally:
        os.close(release)
        os.waitpid(watch, 0)
    with open(os.path.join(directory, 'restoration.json')) as report:
        result = json.load(report)
    result.update(event='closed', session_error=error)
    send(result)
    return result['restore_ok'] and not error


def run(directory, focus):
    v4l2.supported()
    lock = open('/tmp/uwa_wrist_hd_capture.lock', 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        vision.normal(timeout=4)
        settings = vision.settings()
        if settings.get('focusAuto') or settings.get('focus') != focus:
            raise RuntimeError('Expected fixed focus must be applied before session start')
        identity = vision.request('/hello')
        service, pid = vision.service_for_vision()
        return acquire(directory, focus, identity, settings, service, pid)
    finally:
        lock.close()


if __name__ == '__main__':
    try:
        success = run(os.path.dirname(os.path.abspath(__file__)), int(sys.argv[1]))
    except Exception as error:
        send(dict(event='error', error=str(error)))
        success = False
    sys.exit(0 if success else 1)
