#!/usr/bin/env python3
"""Read-only RViz playback of the joint trajectories in a single review revision."""
import argparse
import bisect
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

import numpy as np


class Track:
    """Use the same endpoint derivatives as the joint trajectory controller."""

    def __init__(self, trajectory):
        self.names = trajectory['joint_names']
        points = trajectory['points']
        self.times = [float(point['time']) for point in points]
        if (not self.names or len(set(self.names)) != len(self.names) or not self.times
                or self.times[0] != 0 or not np.isfinite(self.times).all()
                or any(end <= start for start, end in zip(self.times, self.times[1:]))):
            raise ValueError('Invalid joint names or trajectory times')
        self.positions = self.values(points, 'positions')
        self.velocity = self.values(points, 'velocities') if 'velocities' in points[0] else None
        self.accel = self.values(points, 'accelerations') if 'accelerations' in points[0] else None
        if self.accel is not None and self.velocity is None:
            raise ValueError('Acceleration interpolation requires velocities')

    def values(self, points, key):
        data = np.asarray([point[key] for point in points], dtype=float)
        if data.shape != (len(points), len(self.names)) or not np.isfinite(data).all():
            raise ValueError('Incomplete trajectory ' + key)
        return data

    def at(self, seconds):
        if seconds >= self.times[-1] or len(self.times) == 1:
            return self.positions[-1]
        i = max(0, bisect.bisect_right(self.times, seconds) - 1)
        dt = self.times[i + 1] - self.times[i]
        u = max(0., (seconds - self.times[i]) / dt)
        start = self.positions[i]
        delta = self.positions[i + 1] - start
        if self.velocity is None:
            return start + u * delta
        v0, v1 = self.velocity[i:i + 2] * dt
        if self.accel is None:
            return start + (3*u**2 - 2*u**3)*delta + u*(1-u)**2*v0 + u**2*(u-1)*v1
        a0, a1 = self.accel[i:i + 2] * dt**2
        return (start + (10*u**3 - 15*u**4 + 6*u**5)*delta
                + (u - 6*u**3 + 8*u**4 - 3*u**5)*v0 + (-4*u**3 + 7*u**4 - 3*u**5)*v1
                + 0.5*u**2*(1-u)**3*a0 + 0.5*u**3*(1-u)**2*a1)


class Timeline:
    def __init__(self, preview):
        pose = {name: float(q) for name, q in preview['start'].items()}
        if not pose or not np.isfinite(list(pose.values())).all():
            raise ValueError('Missing measured start positions')
        self.groups = []
        self.ends = []
        self.duration = 0.
        for group in preview['groups']:
            tracks = [Track(item) for item in group['trajectories'].values()]
            if not tracks or set(group['arms']) != set(group['trajectories']):
                raise ValueError('Incomplete arm group')
            names = [name for track in tracks for name in track.names]
            if len(names) != len(set(names)) or not set(names) <= pose.keys():
                raise ValueError('Joint names disagree with the group start')
            self.groups.append((group['phase'], list(group['arms']), dict(pose), tracks))
            self.duration += max(track.times[-1] for track in tracks)
            self.ends.append(self.duration)
            for track in tracks:
                pose.update(zip(track.names, track.positions[-1]))
        self.end_pose = pose
        if not math.isclose(self.duration, float(preview['duration_s']), abs_tol=.005):
            raise ValueError('Playback time differs from the reviewed schedule')

    def at(self, seconds):
        if not self.groups:
            return 'Held pose', [], dict(self.end_pose)
        i = min(bisect.bisect_right(self.ends, seconds), len(self.groups) - 1)
        phase, arms, pose, tracks = self.groups[i]
        elapsed = seconds - (self.ends[i - 1] if i else 0.)
        values = dict(pose)
        for track in tracks:
            values.update(zip(track.names, track.at(elapsed)))
        return phase, arms, values


def display_description(description):
    from ament_index_python.packages import get_package_share_directory

    robot = ET.fromstring(description)
    for tag in ('gazebo', 'ros2_control'):
        for child in robot.findall(tag):
            robot.remove(child)
    # The reviewed URDF uses package URIs so the same meshes resolve on both hosts.
    for element in robot.findall('.//mesh'):
        uri = urlsplit(element.get('filename', ''))
        path = Path(uri.path)
        if uri.scheme != 'package':
            raise ValueError('Review requires a portable local mesh: ' + path.name)
        asset = Path(get_package_share_directory(uri.netloc)) / str(path).lstrip('/')
        if '..' in path.parts or not asset.is_file():
            raise ValueError('Missing local preview mesh: ' + path.name)
        element.set('filename', asset.resolve().as_uri())
    return ET.tostring(robot, encoding='unicode')


def view(record, directory):
    import rclpy
    import yaml
    from PySide6 import QtCore, QtWidgets
    from rclpy.qos import QoSProfile, DurabilityPolicy
    from scipy.spatial.transform import Rotation
    from sensor_msgs.msg import JointState
    from visualization_msgs.msg import Marker, MarkerArray

    preview = record['preview']
    timeline = Timeline(preview)
    description = display_description(preview['robot_description'])
    ns = '/uwa_review_' + str(os.getpid())
    params = directory / 'robot.yaml'
    params.write_text(yaml.safe_dump({'/**': {'ros__parameters': {
        'robot_description': description, 'publish_frequency': 30.}}}))
    from ament_index_python.packages import get_package_share_directory
    path = Path(get_package_share_directory('uwa_cell_gazebo')) / 'rviz/cell.rviz'
    config = yaml.safe_load(path.read_text())
    displays = config['Visualization Manager']['Displays']
    grid, model = displays[:2]
    model['Name'] = 'Reviewed trajectory'
    model['Alpha'] = 1.
    model['Description Topic']['Value'] = ns + '/robot_description'
    config['Visualization Manager']['Displays'] = [grid, model, {
        'Class': 'rviz_default_plugins/MarkerArray', 'Name': 'Reviewed carton', 'Enabled': True,
        'Topic': {'Value': ns + '/carton', 'Durability Policy': 'Transient Local', 'Depth': 1}}]
    config_path = directory / 'motion.rviz'
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    rclpy.init(args=[])
    node = rclpy.create_node('review_playback', namespace=ns)
    joints = node.create_publisher(JointState, ns + '/joint_states', 10)
    markers = node.create_publisher(MarkerArray, ns + '/carton',
                QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    carton = preview.get('carton')
    if carton:
        transform = np.asarray(carton['T_world_object'], float)
        boxes = carton.get('shell_boxes') or [{'lo': [0, 0, 0], 'hi': carton['size_m']}]
        rotation = Rotation.from_matrix(transform[:3, :3]).as_quat()
        packet = MarkerArray()
        for index, box in enumerate(boxes):
            lo, hi = np.asarray(box['lo']), np.asarray(box['hi'])
            marker = Marker()
            marker.header.frame_id = 'world'
            marker.id, marker.ns, marker.type = index, 'carton', Marker.CUBE
            center = transform[:3, :3] @ ((lo + hi) / 2) + transform[:3, 3]
            marker.pose.position.x, marker.pose.position.y, marker.pose.position.z = map(float, center)
            orientation = marker.pose.orientation
            orientation.x, orientation.y, orientation.z, orientation.w = map(float, rotation)
            marker.scale.x, marker.scale.y, marker.scale.z = map(float, hi - lo)
            marker.color.r, marker.color.g, marker.color.b, marker.color.a = 1., .65, .18, .6
            packet.markers.append(marker)
        markers.publish(packet)

    app = QtWidgets.QApplication([])
    window = QtWidgets.QWidget()
    window.setWindowTitle('UWA planned motion · ' + record['sha256'][:12])
    layout = QtWidgets.QVBoxLayout(window)
    label = QtWidgets.QLabel()
    label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    layout.addWidget(label)
    slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
    slider.setRange(0, 10_000)
    layout.addWidget(slider)
    buttons = QtWidgets.QHBoxLayout()
    play, rewind = QtWidgets.QPushButton('Play preview'), QtWidgets.QPushButton('Back to start')
    speed = QtWidgets.QComboBox()
    for value in (1, 2, 4, 8):
        speed.addItem(f'{value}× playback', value)
    for widget in (play, rewind, speed):
        buttons.addWidget(widget)
    layout.addLayout(buttons)
    pos = 0.
    playing = False
    last = time.monotonic()

    def seek(value):
        nonlocal pos, playing
        pos = value
        playing = False

    def toggle():
        nonlocal playing, pos, last
        if pos >= timeline.duration:
            pos = 0.
        playing = not playing
        last = time.monotonic()

    play.clicked.connect(toggle)
    rewind.clicked.connect(lambda: seek(0.))
    slider.sliderMoved.connect(lambda value: seek(value * timeline.duration / 10_000))
    children = []

    def tick():
        nonlocal pos, playing, last
        if any(child.poll() is not None for child in children):
            app.quit()
            return
        now = time.monotonic()
        if playing:
            pos = min(timeline.duration, pos + (now - last) * speed.currentData())
        last = now
        if pos >= timeline.duration:
            playing = False
        phase, arms, positions = timeline.at(pos)
        if not slider.isSliderDown():
            slider.setValue(round(10_000 * pos / timeline.duration) if timeline.duration else 0)
        label.setText(f'PREVIEW · {phase} · {", ".join(arms)}\n{pos:.1f} / {timeline.duration:.1f} s · {record["sha256"][:12]}')
        play.setText('Pause' if playing else 'Play preview')
        message = JointState()
        message.header.stamp = node.get_clock().now().to_msg()
        message.name = list(positions)
        message.position = list(positions.values())
        joints.publish(message)
        rclpy.spin_once(node, timeout_sec=0.)

    remaps = ['-r', '/tf:=' + ns + '/tf', '-r', '/tf_static:=' + ns + '/tf_static']
    try:
        children.append(subprocess.Popen(['ros2', 'run', 'robot_state_publisher', 'robot_state_publisher',
            '--ros-args', '--params-file', str(params), '-r', '__ns:=' + ns, *remaps], start_new_session=True))
        children.append(subprocess.Popen(['rviz2', '-d', str(config_path), '--ros-args', *remaps],
                                         start_new_session=True))
        signal.signal(signal.SIGTERM, lambda *_: app.quit())
        signal.signal(signal.SIGINT, lambda *_: app.quit())
        timer = QtCore.QTimer(window)
        timer.timeout.connect(tick)
        timer.start(33)
        window.resize(470, 120)
        window.show()
        tick()
        result = app.exec()
        failed = next((p.returncode for p in children if p.poll() not in (None, 0)), None)
        if failed:
            raise RuntimeError(f'RViz preview process exited ({failed})')
        return result
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
        for child in children:
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        node.destroy_node()
        rclpy.try_shutdown()


def main():
    from motion_review_panel import use_host_desktop_libraries
    use_host_desktop_libraries()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export', type=Path)
    args = parser.parse_args()
    os.environ.update(ROS_DOMAIN_ID='74', ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST')
    with tempfile.TemporaryDirectory(prefix='uwa-motion-review-') as directory:
        return view(json.loads(args.export.read_text()), Path(directory))


if __name__ == '__main__':
    raise SystemExit(main())
