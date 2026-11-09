import pytest
from gz.msgs.camera_info_pb2 import CameraInfo
from gz.msgs.image_pb2 import Image, RGB_INT8

from uwa_cell_gazebo.camera_bridge import image_message, info_message


def test_rgb_payload_optical_frame_and_simulation_stamp_are_preserved():
    source = Image(width=2, height=1, step=6, data=b'\x01\x02\x03\x04\x05\x06',
                   pixel_format_type=RGB_INT8)
    source.header.stamp.sec, source.header.stamp.nsec = 12, 345
    result = image_message(source, 'left_front')
    assert (result.width, result.height, result.step, result.encoding) == (2, 1, 6, 'rgb8')
    assert bytes(result.data) == source.data
    assert result.header.frame_id == 'left_front_wrist_camera_optical_frame'
    assert (result.header.stamp.sec, result.header.stamp.nanosec) == (12, 345)
    source.pixel_format_type = 0
    with pytest.raises(ValueError):
        image_message(source, 'left_front')


def test_camera_calibration_is_transferred_without_reordering():
    source = CameraInfo(width=640, height=480)
    source.intrinsics.k.extend([686., 0., 320., 0., 686., 240., 0., 0., 1.])
    source.projection.p.extend([686., 0., 320., 0., 0., 686., 240., 0., 0., 0., 1., 0.])
    source.distortion.k.extend([0.1, 0.2, 0.3, 0.4, 0.5])
    result = info_message(source, 'right_rear')
    assert list(result.k) == list(source.intrinsics.k)
    assert list(result.p) == list(source.projection.p)
    assert list(result.d) == list(source.distortion.k)
    assert list(result.r) == [1., 0., 0., 0., 1., 0., 0., 0., 1.]
    assert result.header.frame_id == 'right_rear_wrist_camera_optical_frame'
