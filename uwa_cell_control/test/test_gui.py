from pathlib import Path
from python_qt_binding import QtWidgets
from uwa_cell_control.gui import Window


def test_direct_hardware_controls_do_not_require_gui_ownership_or_playing_program():
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    path=Path(__file__).resolve().parents[2]/'config/hardware_inventory.yaml'
    window=Window(path)
    window.timer.stop()
    try:
        assert window.mock and window.selected()==['right_rear']
        assert not window.buttons['prepare'].isEnabled()
        window.mode.setCurrentIndex(1)
        assert window.buttons['prepare'].isEnabled()
        assert window.buttons['play'].isEnabled()
        for key in ['cartesian','trajectory','rqt','joints','load']:
            assert window.buttons[key].isEnabled()
        assert not window.drivers and not window.state
        for rid in window.profiles:window.profiles[rid]['ip']='127.0.0.1'
        window.change_mode()
        for box in window.checks.values():box.setChecked(True)
        assert len(window.selected())==4
        assert window.buttons['cartesian'].isEnabled()
        assert window.buttons['trajectory'].isEnabled()
    finally:window.close()
