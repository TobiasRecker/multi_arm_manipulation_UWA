"""Only pure measurement logic; no ROS context, devices, hosts or commands."""
import importlib.util
import hashlib
import json
from pathlib import Path


path=Path(__file__).resolve().parents[2]/'tools/run_minimal_functional_test.py'
spec=importlib.util.spec_from_file_location('functional_runner_measurements',path)
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def rows(speed=0.):
    return [dict(received=i*.05,device_stamp=100+i*.05,q=[speed*i*.05]*6)
            for i in range(26)]


def test_stop_measurement_requires_advancing_actual_samples_for_a_full_second():
    evidence=runner.quiet_measurement(rows(),after=0.)
    assert evidence['ready'] and evidence['interval_s']>=1.
    assert evidence['samples']>=10 and evidence['max_position_span_rad']==0.
    assert runner.quiet_measurement(rows()[:10],after=0.) is None
    frozen=rows()
    for row in frozen:row['device_stamp']=100.
    assert runner.quiet_measurement(frozen,after=0.) is None


def test_motion_during_pause_does_not_emit_a_stationary_observation():
    evidence=runner.quiet_measurement(rows(.003),after=0.)
    assert not evidence['ready']
    assert evidence['max_position_span_rad']>.0005
    assert max(map(abs,evidence['position_trend_rad_s']))>.0029


def test_relative_cli_paths_are_absolute_before_runtime_model_creation(tmp_path,monkeypatch):
    arms=['left_front','left_rear','right_front','right_rear']
    points=[dict(time=t,positions=[0.]*6,velocities=[0.]*6,accelerations=[0.]*6) for t in (0.,1.)]
    group=dict(arms=arms,trajectories={arm:dict(points=points) for arm in arms})
    body=json.dumps(dict(kind='minimal_four_arm_functional_test',ready=True,
        command_joint_limit_rad_s=.1,groups=[group,group])).encode()
    (tmp_path/'plan.json').write_bytes(body)
    monkeypatch.chdir(tmp_path)
    captured=[]
    monkeypatch.setattr(runner,'execute',lambda args,plan,sha:captured.append(args) or 0)
    assert runner.main(['plan.json','--output','out','--inventory','inventory.yaml',
        '--layout','layout.yaml','--expected-sha256',hashlib.sha256(body).hexdigest(),'--execute'])==0
    args=captured[0]
    assert args.plan==tmp_path/'plan.json' and args.output==tmp_path/'out'
    assert args.inventory==tmp_path/'inventory.yaml' and args.layout==tmp_path/'layout.yaml'
