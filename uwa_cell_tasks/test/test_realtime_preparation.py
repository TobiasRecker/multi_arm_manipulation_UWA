"""Statistics and CLI validation without robot/ROS traffic."""
import importlib.util
from pathlib import Path
import subprocess
import sys

path=Path(__file__).parents[2]/'tools/prepare_realtime.py'
spec=importlib.util.spec_from_file_location('realtime_preparation',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_latency_statistics_keep_tail_and_empty_samples_distinct():
    assert module.stats([])==dict(samples=0)
    result=module.stats([1,2,3,100])
    assert result['maximum']==100 and result['p50']==2.5
    assert result['p99']>97


def test_invalid_probe_deadline_and_existing_output_are_rejected(tmp_path):
    for value in ('0','nan','-1'):
        result=subprocess.run([sys.executable,str(path),'jitter','--period-ms',value,
            '--output',str(tmp_path/'new.json')],capture_output=True)
        assert result.returncode!=0 and not (tmp_path/'new.json').exists()
    target=tmp_path/'evidence.json';target.write_text('preserve')
    result=subprocess.run([sys.executable,str(path),'audit','--output',str(target)],capture_output=True)
    assert result.returncode!=0 and target.read_text()=='preserve'



def test_reaction_chain_rejects_clock_mixing_and_missing_stages():
    import pytest
    stages=['state_received','guard_started','guard_finished','stop_dispatched',
            'deceleration_observed','standstill_observed']
    rows=[dict(trial_id='a',boot_id='one',clock='host_monotonic',stage=k,time_s=t)
        for k,t in zip(stages,[1.,1.002,1.006,1.008,1.012,1.05])]
    result=module.reaction_chain(rows)['trials']['a']
    assert result['state_to_deceleration_ms']==pytest.approx(12.)
    assert result['state_to_standstill_ms']==pytest.approx(50.)
    with pytest.raises(ValueError):module.reaction_chain(rows[:-1])
    with pytest.raises(ValueError):module.reaction_chain(rows+[rows[-1]])
    rows[-1]['boot_id']='two'
    with pytest.raises(ValueError):module.reaction_chain(rows)
    rows[-1]['boot_id']='one';rows[-1]['time_s']=.5
    with pytest.raises(ValueError):module.reaction_chain(rows)
