from pathlib import Path

import pytest
from python_qt_binding import QtCore,QtWidgets
from match_mur_gui.jog_commands import cartesian_twist
from uwa_cell_control.gui import Window
from uwa_cell_control.jog_dialog import JogDialog


class Transport:
    def __init__(self,profile):self.messages=[];self.program_running=None;self.closed=False
    def publish(self,values):self.messages.append(list(values))
    def spin(self):pass
    def subscribers(self):return 0
    def close(self):self.closed=True


def test_shared_mur_mapping_translation_rotation_and_bad_input():
    assert cartesian_twist([1,0,0],'translation',.01,.1)==[.01,0,0,0,0,0]
    assert cartesian_twist([0,-1,0],'rotation',.01,.1)==[0,0,0,0,-.1,0]
    with pytest.raises(ValueError):cartesian_twist([0,float('nan'),0],'rotation',.01,.1)


def test_jog_only_streams_while_held_release_mode_change_focus_and_close_stop(tmp_path,monkeypatch):
    monkeypatch.setenv('UWA_WS',str(tmp_path))
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window=Window(Path(__file__).resolve().parents[2]/'config/hardware_inventory.yaml')
    window.timer.stop();window.closing=True
    dialog=JogDialog(window,'right_rear',transport_factory=Transport);dialog.timer.stop()
    window.jog_dialogs['right_rear']=dialog
    transport=dialog.transport
    try:
        assert not transport.messages
        for _ in range(3):dialog.tick()
        assert not transport.messages  # An idle window must not override another command source.
        dialog.axis_buttons['X+'].pressed.emit();dialog.tick()
        assert transport.messages[-1]==[.01,0,0,0,0,0]
        dialog.axis_buttons['X+'].released.emit()
        assert transport.messages[-1]==[0.]*6
        for _ in range(4):dialog.tick()
        count=len(transport.messages);dialog.tick();assert len(transport.messages)==count
        dialog.mode.setCurrentIndex(1);dialog.start([0,0,1])
        assert transport.messages[-1]==[0,0,0,0,0,.1]
        QtWidgets.QApplication.sendEvent(dialog,QtCore.QEvent(QtCore.QEvent.Type.WindowDeactivate))
        assert transport.messages[-1]==[0.]*6
        dialog.start([1,0,0]);dialog.close()
        assert transport.messages[-1]==[0.]*6 and transport.closed
        assert 'right_rear' not in window.jog_dialogs
    finally:dialog.close();window.close();app.processEvents()
