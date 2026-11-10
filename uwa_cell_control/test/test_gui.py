from pathlib import Path
import os

from python_qt_binding import QtCore,QtWidgets
from uwa_cell_control.gui import Window


def test_four_arm_selection_hardware_unknown_ips_and_mock_only_controls():
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    path=Path(__file__).resolve().parents[2]/'config/hardware_inventory.yaml'
    window=Window(path)
    window.timer.stop()
    try:
        assert window.mock and len(window.selected())==4
        assert not window.buttons['prepare'].isEnabled()
        assert not window.buttons['cartesian'].isEnabled()  # start a driver first
        window.drivers['left_front']=QtCore.QProcess(window)
        for rid,box in window.checks.items():box.setChecked(rid=='left_front')
        assert window.buttons['cartesian'].isEnabled()
        window.checks['right_rear'].setChecked(True)
        assert not window.buttons['cartesian'].isEnabled()  # selected arm not owned
        window.drivers.clear()
        for box in window.checks.values():box.setChecked(True)
        window.update_buttons()
        window.mode.setCurrentIndex(1)
        assert not window.mock
        assert set(window.selected())=={'right_front','right_rear'}
        assert not window.checks['left_front'].isEnabled()
        assert not window.buttons['cartesian'].isEnabled()
        assert not window.buttons['trajectory'].isEnabled()
        assert not window.buttons['prepare'].isEnabled()  # no driver available
    finally:window.close()
