import json
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import power_safety_report as reporter


def journal(stamp, text, pid="1"):
    return dict(__REALTIME_TIMESTAMP=str(int(stamp*1e6)), _PID=pid, MESSAGE=text)


def test_latched_cause_deduplicates_cumulative_records_and_keeps_later_conditions():
    speed = dict(reason='SPEED LIMIT', arms=['right_front'], source_time_s=7.5,
                 measured_velocity_rad_s=.11, configured_limit_rad_s=.1)
    stale = dict(reason='STATE STALE', arms=['left_rear'], source_time_s=10.)
    rows = [journal(9,'STOP LATCHED: '+json.dumps([speed])),
            journal(11,'STOP LATCHED: '+json.dumps([speed, stale])),
            journal(12,'HELD CONDITION: '+json.dumps([dict(stale,reason='DISTANCE',clearance_m=.01)])),
            journal(13,'MONITOR WOULD STOP: '+json.dumps([speed]),'2'),
            journal(14,'STOP LATCHED: malformed')]
    issues = []
    events = reporter.guard_events(rows, issues)
    assert [e['kind'] for e in events] == ['Guard latch','Guard latch','Condition while held','Monitor observation']
    assert events[0]['measurements'] == dict(measured_velocity_rad_s=.11, configured_limit_rad_s=.1)
    assert issues


def test_native_retry_counts_ignore_age_variations_but_keep_distinct_arms_status_and_gaps():
    reason = ('Blocked interlock: manager_fresh=False, hold_config_verified=True, held=False, '
              'controller_error=None, list_age_s=0.31, parameter_age_s=0.32')
    prefix = 'NATIVE STOP REQUESTED right_front: '
    rows = [journal(1,prefix+reason), journal(1.4,prefix+reason.replace('0.31','0.40')),
            journal(1.5,prefix+reason.replace('held=False','held=True')),
            journal(1.6,prefix.replace('right_front','right_rear')+reason), journal(4,prefix+reason)]
    events = reporter.guard_events(rows, [])
    assert [e['count'] for e in events] == [2,1,1,1]
    assert events[0]['first_measurements']['list_age_s'] == .31
    assert events[0]['measurements']['list_age_s'] == .40
    assert events[0]['reason'] != events[1]['reason']


def test_workflow_and_database_report_one_failure_with_native_motion_and_uncertainty(tmp_path, monkeypatch):
    now = time.time()
    run = tmp_path/'setup/tasks/carton_pilot/attempt09'
    (run/'high').mkdir(parents=True)
    workflow = dict(execute=True, error='high failed', updated_wall=reporter.utc(now-1), motion_review='ticket',
                    events=[dict(phase='high',returncode=1,native_motion=dict(available=True,
                                    observed_motion_s={'right_front':3.75, 'right_rear':0}))])
    (run/'workflow.json').write_text(json.dumps(workflow))
    (run/'high/result.json').write_text(json.dumps(dict(arm_commands=[{'arms':['right_front']}],
        error='right_front: time-aligned driver cache differs from independent actual joints',
        state_alignment=dict(right_front=dict(difference_rad=[.004,.002],conservative_difference_rad=[.006,.003])))))
    store = tmp_path/'.local/state/uwa-motion-review'
    store.mkdir(parents=True)
    with sqlite3.connect(store/'reviews.sqlite3') as db:
        db.execute('CREATE TABLE tickets(id,operation,status,reason,changed)')
        db.executemany('INSERT INTO tickets VALUES (?,?,?,?,?)', [
            ('ticket',str(run)+'/motion','failed','high failed',now-1),
            ('block',str(run)+'/issue/123','blocked','high failed',now-1),
            ('prior','task','interrupted','earlier',now-90000)])
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(reporter,'journal_rows',lambda *args:([],False))
    report = reporter.build_report(tmp_path,now=now)
    [event] = report['events']
    assert event['kind'] == 'Execution aborted after observed motion'
    assert event['measurements']['observed_motion_s']['right_front'] == 3.75
    assert event['measurements']['max_conservative_difference_rad'] == .006
    assert '.005' not in event['reason']
    assert report['sources'][0]['status'] == 'missing'


def test_empty_command_and_epoch_evidence_do_not_claim_a_physical_stop():
    record = dict(error='Device epoch changed; regenerate the hardware plan')
    result = dict(arm_commands=[],finger_commands=[],alignment_evidence=dict(
        native_epoch_baseline={'right_front':0},native_records={'right_front':{'epoch':0}},clock_fault_events=[]))
    kind,_,_,data = reporter.workflow_failure(record,result,{})
    assert kind == 'Blocked before phase command'
    assert data['observed_native_epochs'] == {'right_front':0}
    assert 'Not recorded' in data['clock_fault_detail']
    result['arm_commands'] = [{'arms':['right_front']}]
    assert 'unverified' in reporter.workflow_failure(record,result,{})[0]


def test_mock_does_not_open_guard_or_workflows_and_reads_uncheckpointed_wal(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setattr(reporter,'read_guard',lambda *_:pytest.fail('read real host'))
    monkeypatch.setattr(reporter,'workflows',lambda *_:pytest.fail('read real runs'))
    now = time.time()
    db = sqlite3.connect(tmp_path/'reviews.sqlite3')
    try:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE tickets(id,operation,status,reason,changed)')
        db.execute('INSERT INTO tickets VALUES (?,?,?,?,?)',('t','op','pending',None,now-1))
        db.commit()
        report = reporter.build_report(None,tmp_path,now=now)
        assert report['events'][0]['kind'] == 'Awaiting operator review'
        assert report['mode'] == 'mock' and len(report['sources']) == 1
    finally:
        db.close()
    assert reporter.build_report(None,tmp_path/'absent')['sources'][0]['status']=='missing'
    assert not (tmp_path/'absent').exists()


def test_minimal_report_reads_new_unit_without_querying_legacy_guard(tmp_path,monkeypatch):
    now=time.time();queries=[]
    def rows(since,end,pattern=None,*,unit=reporter.UNIT):
        queries.append(unit)
        return [journal(now-2,'All-arm software pause requested: OPERATOR PAUSE'),
                journal(now-1,'Collision data unavailable; no automatic pause: missing sample')],False
    monkeypatch.setattr(reporter,'journal_rows',rows)
    monkeypatch.setenv('HOME',str(tmp_path))
    report=reporter.build_report(tmp_path,now=now,backend='minimal')
    assert queries==[reporter.MINIMAL_UNIT]
    assert report['sources'][0]['name']=='Minimal protection journal'
    assert {row['kind'] for row in report['events']}=={'Software pause requested','Collision data unavailable'}
    pause=next(row for row in report['events'] if row['kind']=='Software pause requested')
    assert pause['reason']=='OPERATOR PAUSE' and pause['standstill_confirmed'] is False
    assert 'session/gui.log' in report['summary_text']
