import json
import pytest

from uwa_cell_tasks.pilot_episode import Episode


def episode(tmp_path, backend='kinematic_model', observables=('agent_intervention',)):
    return Episode.create(tmp_path/'episode', backend=backend, program_sha256='a'*64,
                          observable_events=observables)


def test_unknown_sensing_is_not_zero_and_model_completion_is_distinct(tmp_path):
    e = episode(tmp_path)
    e.append('run_end', phase='end', source='model', model_time_s=12.,
             details=dict(status='MODEL_SEQUENCE_COMPLETE', processing_wall_s=.5))
    s = e.summary()
    assert s['model_duration_s'] == 12 and s['execution_wall_s'] is None
    assert s['processing_wall_s'] == .5
    assert s['detected_events'] == dict(missed_grasp=None, regrasp=None, object_lost=None, agent_intervention=0)
    assert s['force_channels'] == []


def test_kinematic_backend_cannot_claim_contact_sensing_or_success(tmp_path):
    with pytest.raises(ValueError, match='cannot detect'):
        episode(tmp_path, observables=('object_lost',))
    e = episode(tmp_path)
    with pytest.raises(ValueError, match='Physical events'):
        e.append('object_lost', phase='draw', source='sensor')
    with pytest.raises(ValueError, match='no force measurement'):
        e.append('force_sample', phase='draw', source='sensor')
    with pytest.raises(ValueError, match='not physical'):
        e.append('run_end', phase='end', source='model', details=dict(status='DONE'))
    with pytest.raises(ValueError, match='no physical execution'):
        e.append('run_end', phase='end', source='model', details=dict(status='MODEL_SEQUENCE_COMPLETE', execution_wall_s=3))


def test_user_reports_stay_separate_from_detector_counts(tmp_path):
    e = episode(tmp_path, 'contact_simulation', ('object_lost', 'regrasp', 'agent_intervention'))
    e.append('object_lost', phase='hold', source='sensor', details=dict(detector='contact_and_pose'))
    e.append('object_lost', phase='hold', source='user', details=dict(text='I saw it fall'))
    e.append('agent_intervention', phase='recover', source='agent', details=dict(reason='object lost', action='stop'))
    s = e.summary()
    assert s['detected_events']['object_lost'] == 1
    assert s['user_reported_events']['object_lost'] == 1
    assert s['detected_events']['agent_intervention'] == 1
    assert s['detected_events']['missed_grasp'] is None


def test_feedback_after_end_keeps_phase_original_text_and_execution_result(tmp_path):
    e = episode(tmp_path)
    e.append('run_end', phase='end', source='model', model_time_s=12., details=dict(status='MODEL_SEQUENCE_COMPLETE'))
    text = 'Die Drehung war umständlich – andersherum wäre besser.'
    e.append('feedback', phase='return_box', source='user', details=dict(text=text))
    s = e.summary()
    assert s['feedback'][0]['details']['text'] == text
    assert s['feedback'][0]['phase'] == 'return_box'
    assert s['status'] == 'MODEL_SEQUENCE_COMPLETE'
    assert s['feedback'][0]['details']['status'] == 'RECORDED_FOR_REVIEW'
    with pytest.raises(ValueError, match='finished'):
        e.append('regrasp', phase='end', source='user')


def test_force_norm_channels_and_gaps_cannot_be_hidden(tmp_path):
    e = episode(tmp_path, 'contact_simulation', ())
    for sensor, seq, value in [('tcp', 0, 3.), ('tcp', 1, 4.), ('tcp', 3, 2.), ('jaw', 0, 7.)]:
        e.append('force_sample', phase='draw', source='sensor', details=dict(sensor_id=sensor,
                 frame_id='world', reference_point=sensor, quantity='force_norm', sequence=seq,
                 sample_time_s=float(seq), value_n=value))
    tcp, jaw = e.summary()['force_channels']
    assert tcp['max_observed_force_n'] == 4. and not tcp['consecutive_samples']
    assert jaw['max_observed_force_n'] == 7.
    assert 'full execution coverage not established' in tcp['coverage']


def test_manifest_and_event_corruption_are_rejected(tmp_path):
    e = episode(tmp_path)
    e.append('phase_start', phase='draw', source='model', model_time_s=0.)
    path = e.directory/'events.jsonl'
    row = json.loads(path.read_text()); row['phase'] = 'changed'
    path.write_text(json.dumps(row)+'\n')
    with pytest.raises(ValueError, match='chain changed'):
        e.summary()


@pytest.mark.parametrize('bad_time', [-1., float('nan'), float('inf')])
def test_invalid_and_reversed_times_are_rejected(tmp_path, bad_time):
    e = episode(tmp_path)
    with pytest.raises(ValueError, match='Invalid model time'):
        e.append('phase_start', phase='draw', source='model', model_time_s=bad_time)
    e.append('phase_start', phase='draw', source='model', model_time_s=4.)
    with pytest.raises(ValueError, match='backwards'):
        e.append('phase_end', phase='draw', source='model', model_time_s=3.)


def test_completed_directory_and_false_feedback_are_rejected(tmp_path):
    e = episode(tmp_path)
    with pytest.raises(FileExistsError):
        episode(tmp_path)
    for source, text in [('agent', 'good'), ('user', ' ')]:
        with pytest.raises(ValueError, match='user feedback'):
            e.append('feedback', phase='end', source=source, details=dict(text=text))
