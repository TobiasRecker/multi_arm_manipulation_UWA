"""Operator-facing diagnostic exports use isolated Qt processes and local stores."""
import json
import os
from pathlib import Path
import sys
import tarfile
import time

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
REPO = Path(__file__).resolve().parents[2]
for directory in ('scripts', 'uwa_cell_control', 'uwa_cell_tasks'):
    sys.path.insert(0, str(REPO / directory))

from PySide6 import QtWidgets
from motion_review_panel import ReviewPanel
from power_log_view import SafetyLogDialog
from ur_power_gui import Window
from uwa_cell_control.session_logs import SessionLogs
from uwa_cell_tasks.motion_review import ReviewStore, START_PERCENT, TASK


def wait_for(app, condition):
    deadline = time.monotonic() + 6
    while not condition() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert condition()


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(QtWidgets.QSystemTrayIcon, 'isSystemTrayAvailable', lambda: False)
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def exported_files(pointer):
    archive = Path(pointer.read_text().strip())
    assert archive.is_relative_to(pointer.parent / 'exports')
    with tarfile.open(archive) as bundle:
        return {member.name: bundle.extractfile(member).read()
                for member in bundle if member.isfile()}


def test_mock_log_button_saves_report_without_changing_review_or_power(tmp_path, monkeypatch, app):
    monkeypatch.setenv('UWA_WS', str(tmp_path))
    mock = tmp_path / 'mock-review'
    store = ReviewStore(mock)
    store.area('new', True)
    meta = dict(task=TASK, stage='motion', risk='high', reason='Test operator review', components=['mock'],
                arms=['right_front'], duration_s=1., summary='Pending mock approach', speed_percent=START_PERCENT)
    store.submit('pending-test', meta, {'groups': []})
    before = store.status()
    window = Window(review_mock=mock)
    power_starts = []
    window.process.started.connect(lambda: power_starts.append(True))
    pointer = tmp_path / 'setup/logs/uwa-control/latest-export.txt'
    try:
        window.show()
        wait_for(app, lambda: window.review.item and window.review.item['status'] == 'pending')
        window.log_button.click()
        dialog = window.log_view
        wait_for(app, lambda: dialog.isVisible() and dialog.save_button.isEnabled())
        dialog.save_button.click()
        wait_for(app, pointer.exists)
        files = exported_files(pointer)
        report = json.loads(files['session/safety-report.json'])
        assert report['schema_version'] == 1
        assert 'collection_error' not in report
        assert json.loads(files['manifest.json'])['snapshot']['source'] == 'Mock'
        assert report['summary_text'] in files['session/safety-report.txt'].decode()
        assert store.status() == before
        assert not power_starts
        assert not window.refresh_timer.isActive()
    finally:
        if window.log_view:
            window.log_view.close()
        window.finish_quit()
        wait_for(app, lambda: not window.isVisible())


def test_diagnostic_command_failure_can_be_exported(tmp_path, app):
    session = SessionLogs(tmp_path, include_host_logs=False)
    command = [sys.executable, '-c',
               'import sys; sys.stderr.write("test diagnostic connection lost"); sys.exit(23)']
    dialog = SafetyLogDialog(session, command)
    pointer = session.root / 'latest-export.txt'
    try:
        dialog.show()
        wait_for(app, lambda: dialog.save_button.isEnabled()
                 and 'test diagnostic connection lost' in dialog.summary.toPlainText())
        dialog.save_button.click()
        wait_for(app, pointer.exists)
        files = exported_files(pointer)
        error = json.loads(files['session/safety-report.json'])['collection_error']
        assert 'test diagnostic connection lost' in error
        assert error.encode() in files['session/safety-report.txt']
        wait_for(app, lambda: 'Saved with incomplete source data' in dialog.feedback.text())
    finally:
        dialog.shutdown()
        dialog.close()


def test_save_collects_fresh_snapshot_and_marks_unavailable_source(tmp_path, app):
    session = SessionLogs(tmp_path, include_host_logs=False)
    data = tmp_path / 'report.json'
    report = dict(schema_version=1, summary_text='First diagnostic snapshot',
                  sources=[{'name': 'watchdog', 'status': 'ok'}], events=[], grouped=[])
    data.write_text(json.dumps(report))
    dialog = SafetyLogDialog(session, ['/usr/bin/cat', str(data)])
    pointer = session.root / 'latest-export.txt'
    try:
        dialog.show()
        wait_for(app, lambda: 'First diagnostic snapshot' in dialog.summary.toPlainText())
        report['summary_text'] = 'Position check blocked the approach. Watchdog records unavailable.'
        report['sources'][0]['status'] = 'unavailable'
        report['events'].append({'phase': 'high', 'outcome': 'blocked'})
        data.write_text(json.dumps(report))
        dialog.save_button.click()
        wait_for(app, pointer.exists)
        files = exported_files(pointer)
        assert json.loads(files['session/safety-report.json']) == report
        wait_for(app, lambda: 'Saved with incomplete source data' in dialog.feedback.text())
    finally:
        dialog.shutdown()
        dialog.close()


def test_close_while_loading_leaves_gui_responsive(tmp_path, app):
    session = SessionLogs(tmp_path, include_host_logs=False)
    started = tmp_path / 'running'
    release = tmp_path / 'release'
    command = [sys.executable, '-c',
               'from pathlib import Path\nimport sys,time\nPath(sys.argv[1]).touch()\n'
               'while not Path(sys.argv[2]).exists(): time.sleep(.01)', str(started), str(release)]
    dialog = SafetyLogDialog(session, command)
    try:
        dialog.show()
        wait_for(app, started.exists)
        dialog.close()
        assert not dialog.isVisible()
        assert not (session.root / 'latest-export.txt').exists()
    finally:
        release.touch()
        dialog.shutdown()


def test_review_status_announces_only_new_decisions_and_new_faults(tmp_path, monkeypatch, app):
    store = ReviewStore(tmp_path / 'mock-review')
    status = store.status()
    old = dict(id='historic', status='failed', reason='Previous shift stopped', actor=None)
    status['history'] = [old]
    monkeypatch.setattr(ReviewPanel, 'refresh', lambda self: None)
    panel = ReviewPanel([])
    decisions, warnings = [], []
    panel.attention.connect(decisions.append)
    panel.faultNotice.connect(warnings.append)
    try:
        panel.render_status(status)
        assert old['reason'] in panel.details.text()
        assert not warnings and not decisions

        for outcome in ('blocked', 'failed', 'interrupted'):
            reason = 'New test run ' + outcome
            status['history'].insert(0, dict(id='run-' + outcome, status=outcome, reason=reason, actor=None))
            count = len(warnings)
            panel.render_status(status)
            panel.render_status(status)
            assert len(warnings) == count + 1 and reason in warnings[-1]
            assert not decisions

        meta = dict(task=TASK, stage='motion', risk='high', reason='Inspect the new plan', components=['mock'],
                    arms=['right_front'], duration_s=1., summary='Pending operator decision', speed_percent=START_PERCENT)
        store.submit('new-test-review', meta, {'groups': []})
        status['pending'] = store.status()['pending']
        panel.render_status(status)
        panel.render_status(status)
        assert decisions == [meta['summary']]
        assert len(warnings) == 3
        status['pending'][0]['status'] = 'approved'
        panel.render_status(status)
        assert decisions == [meta['summary']]
    finally:
        panel.shutdown()

