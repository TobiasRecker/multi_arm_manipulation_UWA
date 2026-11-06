"""Optional live integration check; not part of the offline pytest collection.

Run with the simulated cell active and QT_QPA_PLATFORM=offscreen. Uses the
installed standard rqt plugin, selects each real simulated controller, and
checks the emitted command topic while holding its current position.
"""
import os
from pathlib import Path
import time

import numpy as np
import rclpy
import rclpy.node
from python_qt_binding.QtWidgets import QApplication
from python_qt_binding.QtCore import QCoreApplication, QEvent, QObject
from rqt_joint_trajectory_controller.joint_trajectory_controller import JointTrajectoryController
from trajectory_msgs.msg import JointTrajectory


class Context(QObject):
    def serial_number(self):
        return 1

    def add_widget(self, widget):
        self.widget = widget


def main():
    assert os.environ.get('ROS_DOMAIN_ID') == '64', 'Only run in the simulated domain 64'
    app = QApplication([])
    rclpy.init(args=['--ros-args', '-r', '__ns:=/uwa_cell'])
    context = Context()
    plugin = JointTrajectoryController(context)
    observer = rclpy.create_node('uwa_rqt_test_observer')

    def until(condition, timeout=25):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            app.processEvents()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            rclpy.spin_once(observer, timeout_sec=.03)
            if condition():
                return
        raise TimeoutError('rqt did not discover/populate the simulated controllers')

    try:
        context.widget.resize(850, 600)
        context.widget.show()
        combo = context.widget.cm_combo
        until(lambda: combo.findText('/uwa_cell/controller_manager') >= 0)
        combo.setCurrentIndex(combo.findText('/uwa_cell/controller_manager'))
        controllers = context.widget.jtc_combo
        until(lambda: controllers.count() == 4)
        names = [controllers.itemText(i) for i in range(controllers.count())]
        assert len(set(names)) == 4
        for name in names:
            controllers.setCurrentIndex(controllers.findText(name))
            until(lambda: len(plugin._joint_names) == 6 and
                  all('position' in plugin._joint_pos[j] for j in plugin._joint_names))
            assert len(list(plugin._joint_widgets())) == 6
            # Let the monitor timer populate the editors before enabling output.
            until(lambda: all(abs(widget.value() - plugin._joint_pos[joint]['position']) < 1e-4
                              for joint, widget in zip(plugin._joint_names,
                                                       plugin._joint_widgets())))
            held = [plugin._joint_pos[joint]['position'] for joint in plugin._joint_names]
            received = []
            subscription = observer.create_subscription(
                JointTrajectory, f'/uwa_cell/{name}/joint_trajectory', received.append, 1)
            context.widget.enable_button.setChecked(True)
            try:
                until(lambda: bool(received))
                message = received[-1]
                assert len(message.joint_names) == 6
                assert np.isfinite(message.points[0].positions).all()
                np.testing.assert_allclose(message.points[0].positions, held, atol=1e-4)
            finally:
                context.widget.enable_button.setChecked(False)
                observer.destroy_subscription(subscription)
            print(f'rqt selector, six editors and command publishing verified: {name}', flush=True)
        screenshot = os.environ.get('UWA_RQT_SCREENSHOT')
        if screenshot:
            assert context.widget.grab().save(str(Path(screenshot)))
    finally:
        plugin.shutdown_plugin()
        context.widget.close()
        observer.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
