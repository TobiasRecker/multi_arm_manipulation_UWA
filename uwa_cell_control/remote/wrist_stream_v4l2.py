"""Persistent native MJPEG on the UR controllers' Linux x86 V4L2 ABIs (Python 2.7/3)."""
from __future__ import print_function
import base64
import errno
import mmap
import os
import platform
import struct
import sys

from wrist_capture_i686_fast import CAPTURE, MMAP, MJPEG, SIZE, buf, ioctl

# v4l2_format's union is pointer-aligned. v4l2_buffer contains a native
# timeval and an unsigned-long union. The CB3 runs the i386 time32 ABI.
POINTER = struct.calcsize('P')
FORMAT_SIZE, PIX_OFFSET = (208, 8) if POINTER == 8 else (204, 4)
BUFFER_SIZE, TIME_OFFSET, SEQUENCE_OFFSET, MEMORY_OFFSET, MAP_OFFSET, LENGTH_OFFSET = (
    (88, 24, 56, 60, 64, 72) if POINTER == 8 else (68, 20, 44, 48, 52, 56))


def supported():
    if (platform.system() != 'Linux' or sys.byteorder != 'little' or POINTER not in (4, 8)
            or platform.machine() not in ('i386', 'i486', 'i586', 'i686', 'x86_64', 'amd64')):
        raise RuntimeError('Unsupported V4L2 ABI')


def device():
    return os.open('/dev/video0', os.O_RDWR | os.O_NONBLOCK)


def mode(fd):
    return ioctl(fd, 4, buf(FORMAT_SIZE, CAPTURE)), ioctl(fd, 21, buf(204, CAPTURE))


def describe(pair):
    fmt, rate = pair
    return struct.unpack_from('<III', fmt, PIX_OFFSET), struct.unpack_from('<II', rate, 12)


def saveable(pair):
    return [base64.b64encode(data).decode('ascii') for data in pair]


def check_mode(original, apply=False):
    fd = device()
    try:
        if apply:
            ioctl(fd, 5, original[0]); ioctl(fd, 22, original[1])
        fmt, rate = describe(mode(fd))
        old_fmt, old_rate = describe(original)
        if fmt != old_fmt or not all(rate + old_rate) or rate[0]*old_rate[1] != rate[1]*old_rate[0]:
            raise RuntimeError('Wrist V4L2 format or rate differs from the saved mode')
        return dict(verified=True, image_size=list(fmt[:2]), fourcc=fmt[2], frame_interval=list(rate))
    finally:
        os.close(fd)


def sensor_controls(fd):
    values = {}
    for name, cid in (('focus_absolute', 0x009a090a), ('focus_auto', 0x009a090c),
                      ('exposure_absolute', 0x009a0902), ('exposure_auto', 0x009a0901),
                      ('gain', 0x00980913), ('white_balance_auto', 0x0098090c),
                      ('white_balance_temperature', 0x0098091a)):
        try:
            values[name] = struct.unpack_from('<i', ioctl(fd, 27, buf(8, cid)), 4)[0]
        except IOError:
            continue
    return values


def buffer(index=0):
    data = buf(BUFFER_SIZE, index, CAPTURE)
    struct.pack_into('<I', data, MEMORY_OFFSET, MMAP)
    return data


class Camera:
    def __init__(self):
        self.fd = device()
        self.maps = []
        self.streaming = False

    def start(self):
        old, rate = mode(self.fd)
        fmt = bytearray(old)
        struct.pack_into('<IIII', fmt, PIX_OFFSET, SIZE[0], SIZE[1], MJPEG, 0)
        negotiated = ioctl(self.fd, 5, fmt)
        if struct.unpack_from('<III', negotiated, PIX_OFFSET) != SIZE + (MJPEG,):
            raise RuntimeError('Native MJPEG format was refused')
        rate = bytearray(rate)
        struct.pack_into('<II', rate, 12, 1, 15)
        ioctl(self.fd, 22, rate)
        count = struct.unpack_from('<I', ioctl(self.fd, 8, buf(20, 4, CAPTURE, MMAP)))[0]
        if not 2 <= count <= 4:
            raise RuntimeError('Invalid mmap buffer count')
        for index in range(count):
            data = ioctl(self.fd, 9, buffer(index))
            length = struct.unpack_from('<I', data, LENGTH_OFFSET)[0]
            offset = struct.unpack_from('<I', data, MAP_OFFSET)[0]
            if not 0 < length <= 32 * 1024 * 1024:
                raise RuntimeError('Invalid mmap buffer length')
            self.maps.append(mmap.mmap(self.fd, length, mmap.MAP_SHARED,
                                       mmap.PROT_READ | mmap.PROT_WRITE, offset=offset))
            ioctl(self.fd, 15, data)
        ioctl(self.fd, 18, buf(4, CAPTURE), direction=1)
        self.streaming = True

    def dequeue(self, copy_image):
        try:
            data = ioctl(self.fd, 17, buffer())
        except IOError as error:
            if error.errno == errno.EAGAIN:
                return None
            raise
        index, _, used, flags = struct.unpack_from('<IIII', data)
        try:
            if index >= len(self.maps):
                raise RuntimeError('Invalid mmap buffer index')
            if flags & 0x40 or not 2 < used <= len(self.maps[index]):
                return None
            if self.maps[index][:2] != b'\xff\xd8':
                return None
            if copy_image and self.maps[index].find(b'\xff\xd9', 2, used) < 0:
                return None
            sequence = struct.unpack_from('<I', data, SEQUENCE_OFFSET)[0]
            sec, usec = struct.unpack_from('@ll', data, TIME_OFFSET)
            meta = dict(device_sequence=sequence, device_timestamp_seconds=sec+usec/1e6,
                        device_buffer_flags=flags, image_size=list(SIZE))
            return meta, self.maps[index][:used] if copy_image else None
        finally:
            ioctl(self.fd, 15, data)

    def close(self):
        try:
            if self.streaming:
                ioctl(self.fd, 19, buf(4, CAPTURE), direction=1)
        finally:
            try:
                for mapping in self.maps:
                    mapping.close()
            finally:
                os.close(self.fd)
