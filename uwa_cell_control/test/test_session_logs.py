import json
import os
from pathlib import Path
import tarfile
import time

from uwa_cell_control.session_logs import SessionLogs


def test_export_separates_sessions_and_filters_ros_history(tmp_path,monkeypatch):
    import uwa_cell_control.session_logs as logs
    monkeypatch.setattr(logs,'active_ros_logs',lambda *args:set())
    ros=tmp_path/'ros';ros.mkdir()
    old=ros/'old.log';old.write_text('old history');os.utime(old,(1,1))
    legacy=tmp_path/'setup/logs/uwa-control/gui.log';legacy.parent.mkdir(parents=True)
    legacy.write_text('old attached-driver context')
    first=SessionLogs(tmp_path,ros_root=ros);second=SessionLogs(tmp_path,ros_root=ros)
    second.note('another session')
    first.note('first message');first.note('last message')
    current=ros/'current.log';current.write_text('current ROS failure')
    os.utime(current,(first.started+1,first.started+1))
    outside=tmp_path/'outside.log';outside.write_text('not ROS data')
    (ros/'linked.log').symlink_to(outside)
    inherited=ros/'attached.log';inherited.write_text('older active driver');os.utime(inherited,(1,1))
    first.inherited.add(inherited.resolve())
    destination=first.export({'mode':'mock','selected_arms':['right_rear']})
    with tarfile.open(destination) as archive:
        names=archive.getnames()
        assert 'ros/current.log' in names and 'ros/attached.log' in names
        assert 'ros/old.log' not in names and 'ros/linked.log' not in names
        assert archive.extractfile('session/gui.log').read()==b'first message\nlast message\n'
        manifest=json.load(archive.extractfile('manifest.json'))
        assert manifest['session_id']==first.id
        assert manifest['snapshot']['selected_arms']==['right_rear']
        assert 'inherited_context/legacy_gui.log' in names
    assert Path((first.root/'latest-export.txt').read_text().strip())==destination
    assert first.export({})!=destination  # repeated exports never overwrite a snapshot


def test_save_logs_button_captures_failure_output_without_blocking_commands(tmp_path,monkeypatch):
    from python_qt_binding import QtWidgets,QtCore
    from uwa_cell_control.gui import Window
    monkeypatch.setenv('UWA_WS',str(tmp_path))
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    inventory=Path(__file__).resolve().parents[2]/'config/hardware_inventory.yaml'
    window=Window(inventory);window.timer.stop();window.closing=True
    completed=[]
    try:
        assert window.save_logs_button.text()=='Save logs'
        assert window.checks['right_rear'].text()=='Right rear'
        assert window.tabs.tabText(0)=='Preparation'
        process=window.process(['/usr/bin/python3','-c',
            "import sys; print('diagnostic stdout'); print('failure detail',file=sys.stderr); sys.exit(3)"],
            tag='status',finished=lambda *args:completed.append(args))
        end=time.monotonic()+5
        while not completed and time.monotonic()<end:app.processEvents();time.sleep(.01)
        assert completed and completed[0][0]==3
        window.jobs['load']=QtCore.QProcess(window);window.update_buttons()
        assert window.save_logs_button.isEnabled()  # available during an operation
        window.save_logs_button.click()
        end=time.monotonic()+10
        while window.export_worker is not None and time.monotonic()<end:
            app.processEvents();time.sleep(.01)
        assert window.export_worker is None and window.save_logs_button.isEnabled()
        archive_path=Path((window.session.root/'latest-export.txt').read_text().strip())
        with tarfile.open(archive_path) as archive:
            data=archive.extractfile('session/processes/0001-status.log').read().decode()
            assert 'diagnostic stdout' in data and 'failure detail' in data and 'Exit code: 3' in data
            assert 'session/gui.png' in archive.getnames()
            assert json.load(archive.extractfile('manifest.json'))['snapshot']['mode']=='mock'
        assert 'Saved:' in window.export_label.text()
    finally:
        if window.export_worker is not None:
            window.export_worker.wait(10000);app.processEvents()
        window.jobs.clear();window.close();app.processEvents()
