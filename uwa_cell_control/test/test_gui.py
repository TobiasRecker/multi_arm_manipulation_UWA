from pathlib import Path
import os

from python_qt_binding import QtWidgets
from uwa_cell_control.gui import Window


def test_four_arm_selection_hardware_unknown_ips_and_mock_only_controls():
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    path=Path(__file__).resolve().parents[2]/'config/hardware_inventory.yaml'
    window=Window(path)
    window.timer.stop()
    try:
        assert window.mock and len(window.selected())==4
        assert not window.buttons['prepare'].isEnabled()
        assert window.buttons['cartesian'].isEnabled()
        window.mode.setCurrentIndex(1)
        assert not window.mock
        assert set(window.selected())=={'right_front','right_rear'}
        assert not window.checks['left_front'].isEnabled()
        assert not window.buttons['cartesian'].isEnabled()
        assert not window.buttons['trajectory'].isEnabled()
        assert window.buttons['prepare'].isEnabled()
    finally:window.close()
