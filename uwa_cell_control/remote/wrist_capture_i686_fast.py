#!/usr/bin/python
"""Native single-planar MJPEG capture for the i686 CB3 Linux time32 ABI.

Python 2.7 compatible. No robot interfaces. Used inside wrist_worker's camera
transaction, with the same output and cleanup contract as wrist_capture.c.
"""
from __future__ import print_function
import base64
import ctypes
import errno
import json
import mmap
import os
import platform
import select
import struct
import sys

CAPTURE, MMAP = 1, 1
MJPEG = struct.unpack('<I', b'MJPG')[0]
SIZE = (2592, 1944)
# i386 UAPI layout: v4l2_format includes a 200-byte union; v4l2_buffer
# contains a 32-bit timeval and single-planar 32-bit mmap offset.
FMT, STREAM_PARM, REQ, BUFFER = 204, 204, 20, 68
LIBC_IOCTL = ctypes.CDLL(None, use_errno=True).ioctl
LIBC_IOCTL.argtypes = (ctypes.c_int, ctypes.c_ulong, ctypes.c_void_p)
LIBC_IOCTL.restype = ctypes.c_int


def check_abi():
    if platform.system() != 'Linux' or platform.machine() not in ('i386', 'i486', 'i586', 'i686') or struct.calcsize('P') != 4 or sys.byteorder != 'little':
        raise RuntimeError('This helper requires the CB3 i686 Linux ABI')


def ioctl(fd, nr, data, direction=3):
    code = (direction << 30) | (len(data) << 16) | (ord('V') << 8) | nr
    # Python 2.7's fcntl wrapper on i686 rejects some unsigned ioctl codes.
    data = bytearray(data)
    backing = (ctypes.c_char * len(data)).from_buffer(data)
    while True:
        if LIBC_IOCTL(fd, code, backing) >= 0:
            return bytes(data)
        failure = ctypes.get_errno()
        if failure != errno.EINTR:
            operation = {5: "S_FMT", 8: "REQBUFS", 9: "QUERYBUF", 15: "QBUF",
                         17: "DQBUF", 18: "STREAMON", 19: "STREAMOFF"}.get(nr, "ioctl %d" % nr)
            raise IOError(failure, "%s: %s" % (operation, os.strerror(failure)))


def buf(size, *values):
    data = bytearray(size)
    if values:
        struct.pack_into('<' + 'I' * len(values), data, 0, *values)
    return data


def wanted(old):
    result = bytearray(old)
    struct.pack_into('<IIII', result, 4, SIZE[0], SIZE[1], MJPEG, 0)
    return result


def fmt(data):
    return struct.unpack_from('<III', data, 4)


def probe(fd):
    old = ioctl(fd, 4, buf(FMT, CAPTURE))
    trial = ioctl(fd, 64, wanted(old))  # VIDIOC_TRY_FMT does not change the device.
    return dict(current=fmt(old), trial=fmt(trial), native=fmt(trial) == SIZE + (MJPEG,))


def controls(fd, frame):
    values = {'frame': frame}
    for name, cid in (('focus_absolute', 0x009a090a), ('focus_auto', 0x009a090c),
                      ('exposure_absolute', 0x009a0902), ('exposure_auto', 0x009a0901),
                      ('gain', 0x00980913), ('white_balance_auto', 0x0098090c),
                      ('white_balance_temperature', 0x0098091a)):
        try:
            data = ioctl(fd, 27, buf(8, cid))  # VIDIOC_G_CTRL
        except IOError:
            continue  # Driver need not expose a particular control.
        values[name] = struct.unpack_from('<i', data, 4)[0]
    print('CONTROLS ' + json.dumps(values, sort_keys=True)); sys.stdout.flush()


def mmap_buffer(index=0):
    data = buf(BUFFER, index, CAPTURE)
    struct.pack_into('<I', data, 48, MMAP)
    return data


def capture(fd, directory):
    controls(fd, -2)
    old = ioctl(fd, 4, buf(FMT, CAPTURE))
    try:
        parm = ioctl(fd, 21, buf(STREAM_PARM, CAPTURE))
    except IOError:
        parm = None
    with open(os.path.join(directory, 'original-v4l2-mode.json'), 'w') as stream:
        json.dump({'format': base64.b64encode(old).decode('ascii'),
                   'rate': base64.b64encode(parm).decode('ascii') if parm else None}, stream)
    changed = allocated = streaming = False
    maps = []
    cleanup_errors = []
    try:
        data = ioctl(fd, 5, wanted(old)); changed = True
        if fmt(data) != SIZE + (MJPEG,):
            raise RuntimeError('Requested native format not accepted: %r' % (fmt(data),))
        print('NEGOTIATED width=2592 height=1944 sizeimage=%d' % struct.unpack_from('<I', data, 24)[0]); sys.stdout.flush()
        if parm is not None:
            rate = bytearray(parm)
            struct.pack_into('<II', rate, 12, 1, 15)
            ioctl(fd, 22, rate)
        request = ioctl(fd, 8, buf(REQ, 4, CAPTURE, MMAP)); allocated = True
        count = struct.unpack_from('<I', request)[0]
        if not 2 <= count <= 4:
            raise RuntimeError('Unexpected mmap buffer count')
        for index in range(count):
            data = ioctl(fd, 9, mmap_buffer(index))
            offset, length = struct.unpack_from('<II', data, 52)
            if not 0 < length <= 32 * 1024 * 1024:
                raise RuntimeError('Invalid mmap buffer length')
            maps.append(mmap.mmap(fd, length, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=offset))
            ioctl(fd, 15, data)
        ioctl(fd, 18, buf(4, CAPTURE), direction=1); streaming = True
        poll = select.poll(); poll.register(fd, select.POLLIN)
        for frame in range(6):
            if not poll.poll(2000):
                raise RuntimeError('Native frame timeout')
            data = ioctl(fd, 17, mmap_buffer())
            index, _, used, flags = struct.unpack_from('<IIII', data)
            sec, usec = struct.unpack_from('<ii', data, 20)
            sequence = struct.unpack_from('<I', data, 44)[0]
            if index >= len(maps) or not 2 < used <= len(maps[index]) or flags & 0x40:
                raise RuntimeError('Invalid native buffer')
            print('FRAME %d bytes=%d sequence=%d flags=%d timestamp=%d.%06d' % (frame, used, sequence, flags, sec, usec));sys.stdout.flush()
            if frame >= 3:
                if frame in (3, 5):controls(fd, frame)
                jpeg = maps[index][:used]
                if not jpeg.startswith(b'\xff\xd8'):
                    raise RuntimeError('Native buffer is not JPEG')
                with open(os.path.join(directory, 'frame_%03d.jpg' % (frame - 3)), 'wb') as stream:
                    stream.write(jpeg)
            ioctl(fd, 15, data)
    finally:
        def attempt(label, op):
            try:op()
            except Exception as error:cleanup_errors.append('%s: %s' % (label, error))
        if streaming:attempt('STREAMOFF', lambda:ioctl(fd, 19, buf(4, CAPTURE), direction=1))
        for mapped in maps:attempt('munmap', mapped.close)
        if allocated:attempt('free buffers', lambda:ioctl(fd, 8, buf(REQ, 0, CAPTURE, MMAP)))
        if changed:
            print('DEFERRED_FORMAT_RESTORE %ux%u via visionserver; verification required' % fmt(old)[:2])
        if cleanup_errors:
            print("CLEANUP_ERROR " + "; ".join(cleanup_errors), file=sys.stderr)
            if sys.exc_info()[0] is None:
                raise RuntimeError("Native stream cleanup failed")



def mode_command(fd, command, directory):
    with open(os.path.join(directory, 'original-v4l2-mode.json')) as stream:
        saved = json.load(stream)
    old = base64.b64decode(saved['format'])
    parm = base64.b64decode(saved['rate']) if saved['rate'] else None
    if command == '--restore-mode':
        ioctl(fd, 5, old)
        if parm is not None:
            ioctl(fd, 22, parm)
    actual = ioctl(fd, 4, buf(FMT, CAPTURE))
    if fmt(actual) != fmt(old):
        raise RuntimeError('Restored format differs from original')
    interval = [0, 0]
    if parm is not None:
        rate = ioctl(fd, 21, buf(STREAM_PARM, CAPTURE))
        interval = list(struct.unpack_from('<II', rate, 12))
        expected = struct.unpack_from('<II', parm, 12)
        if not all(interval + list(expected)) or interval[0] * expected[1] != expected[0] * interval[1]:
            raise RuntimeError('Restored frame interval differs from original')
    print(json.dumps({'verified': True, 'width': fmt(actual)[0], 'height': fmt(actual)[1],
                      'fourcc': fmt(actual)[2], 'frame_interval': interval}))

if __name__ == '__main__':
    check_abi()
    if len(sys.argv) == 4 and sys.argv[1] in ('--verify-mode', '--restore-mode'):
        fd = os.open(sys.argv[2], os.O_RDWR | os.O_NONBLOCK)
        try:mode_command(fd, sys.argv[1], sys.argv[3])
        finally:os.close(fd)
        raise SystemExit(0)
    if len(sys.argv) != 3 or '/dev/video0' not in sys.argv[1:]:
        raise SystemExit('Usage: wrist_capture --probe /dev/video0 | /dev/video0 OUTPUT_DIRECTORY')
    checking = sys.argv[1] == '--probe'
    fd = os.open('/dev/video0', (os.O_RDONLY if checking else os.O_RDWR) | os.O_NONBLOCK)
    try:
        if checking:print(json.dumps(probe(fd)))
        else:capture(fd, sys.argv[2])
    finally:os.close(fd)
