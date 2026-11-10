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
        assert window.ros_domain==67
        assert not window.buttons['prepare'].isEnabled()
        window.mode.setCurrentIndex(1)
        assert window.ros_domain==66
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


def test_click_feedback_is_persistent_and_auto_status_does_not_replace_it(tmp_path,monkeypatch):
    import json,time
    monkeypatch.setenv('UWA_WS',str(tmp_path))
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    inventory=Path(__file__).resolve().parents[2]/'config/hardware_inventory.yaml'
    window=Window(inventory);window.timer.stop();window.closing=True
    try:
        window.acknowledge('prepare','Prepare UR',window.buttons['prepare'])
        assert window.feedback.phase=='RECEIVED'
        assert 'Click received' in window.feedback.detail.text()
        callbacks=[]
        monkeypatch.setattr(window,'process',lambda args,tag,finished:callbacks.append(finished))
        window.operation('prepare')
        assert window.feedback.phase=='RUNNING'
        callbacks.pop()(1,json.dumps({'arms':{'right_rear':{'error':'UR service unavailable'}}}))
        assert window.feedback.phase=='FAILED'
        assert 'UR service unavailable' in window.feedback.detail.text()
        window.operation('status')
        callbacks.pop()(0,json.dumps({'arms':{}}))
        assert window.feedback.phase=='FAILED'  # Background status must not hide the error.
        window.buttons['status'].setEnabled(True)
        window.acknowledge('status','Check status',window.buttons['status'])
        window.operation('status');callbacks.pop()(0,json.dumps({'arms':{}}))
        assert window.feedback.phase=='DONE'
        assert 'Button pressed: Prepare UR' in window.session.gui_log.read_text()
        window.grab().save(str(tmp_path/'feedback.png'))
    finally:
        window.jobs.clear();window.close();app.processEvents()
