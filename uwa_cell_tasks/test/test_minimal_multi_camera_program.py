"""Current camera library uses shared state and frozen serial minimal execution."""
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace as Box

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'tools'))
from uwa_cell_motion.common import ROBOT_IDS, joint_names
from uwa_cell_motion import minimal_execution
from uwa_cell_tasks import minimal_snapshot
import observe_calibration_start as observer
import execute_calibration_observation_motion as executor
import prepare_calibration_observation_motion as compiler
import run_multi_camera_program as library


def forbidden(*a,**k):
    pytest.fail('Legacy protection or extra device observation was invoked')


def test_minimal_observation_reads_shared_current_joints_without_native_or_rest_tests(tmp_path,monkeypatch):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    monkeypatch.setenv('UWA_MINIMAL_RUNTIME',str(tmp_path/'candidate'))
    names={arm:joint_names(arm) for arm in ROBOT_IDS}
    problem=Box(description='<robot name="mock"><link name="world"/></robot>',cfg={},
        inventory='candidate/inventory.yaml',binding='binding',signature='model',names=names,
        spheres=Box(geometry=Box(assets={})))
    seen=[]
    monkeypatch.setattr(observer,'require_domain',lambda mode:seen.append(mode))
    monkeypatch.setattr(observer,'released_area',lambda expected=None:dict(area_released=True,session_id='area'))
    monkeypatch.setattr(observer,'config',lambda path:dict(command_velocity_limit_rad_s=.1))
    monkeypatch.setattr(observer,'HardwareProblem',lambda *a:problem)
    monkeypatch.setattr(observer,'signature',lambda *a:'hardware-identity')
    monkeypatch.setattr(observer,'MODULES',[])
    monkeypatch.setattr(observer,'RtdeStates',forbidden)
    monkeypatch.setattr(observer,'GuardState',forbidden)
    snapshot=dict(model_signature='model',arms={arm:dict(samples=[dict(actual_q=[.2]*6,
        actual_qd=[.99]*6,device_timestamp_s=5.,received_monotonic_s=42.)]) for arm in ROBOT_IDS})
    monkeypatch.setattr(minimal_snapshot,'observe',lambda:snapshot)
    observer.observe(tmp_path/'observation')
    saved=json.loads((tmp_path/'observation/snapshot.json').read_text())
    assert saved['protection_backend']=='minimal' and saved['area_session']=='area'
    assert set(saved['source_records'])==set(ROBOT_IDS)
    assert all('status' not in row for row in saved['source_records'].values())
    assert all(row['v']==[.99]*6 for row in saved['source_records'].values())
    assert 'stationarity' not in saved and all(q==.2 for q in saved['start'].values())
    context=json.loads((tmp_path/'observation/model-context.json').read_text())
    assert context['hardware_binding']=='binding' and context['model_signature']=='model'
    assert seen==['hardware']


def frozen_plans(directory):
    directory.mkdir()
    state={joint:0. for arm in ROBOT_IDS for joint in joint_names(arm)}
    segments=[]
    for i,arm in enumerate(ROBOT_IDS):
        target=[.05]*6
        plan=dict(success=True,hardware_plan=True,execution_mode='hardware',compiled_command_limit_rad_s=.09,
            hardware_binding='binding',mesh_sha256={},config=dict(acceleration_limit_rad_s2=.2),inventory='inventory',
            metrics=dict(full_cell_collision_checked=True),request=dict(selected=[arm],start=dict(state),goals={arm:target}),
            trajectory=dict(joint_names=joint_names(arm),duration_s=2.,points=[
                dict(time=0.,positions=[state[j] for j in joint_names(arm)],velocities=[0.]*6,accelerations=[0.]*6),
                dict(time=2.,positions=target,velocities=[0.]*6,accelerations=[0.]*6)]),
            portable_binding=dict(exact_planner_modules={}))
        file=directory/(str(i)+'-'+arm+'.json')
        file.write_text(json.dumps(plan))
        segments.append(dict(arm=arm,plan=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
        state.update(zip(joint_names(arm),target))
    sequence=directory/'sequence.json'
    sequence.write_text(json.dumps(dict(command_velocity_limit_rad_s=.09,segments=segments)))
    return hashlib.sha256(sequence.read_bytes()).hexdigest()


def test_four_frozen_camera_paths_route_serially_without_old_monitors_or_retiming(tmp_path,monkeypatch):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    digest=frozen_plans(tmp_path/'plans')
    _,plans=executor.checked_plans(tmp_path/'plans',digest,.09)
    before=json.dumps(plans,sort_keys=True)
    calls=[]
    problem=Box(names={arm:joint_names(arm) for arm in ROBOT_IDS},binding='binding',
        spheres=Box(geometry=Box(assets={})),cfg=dict(acceleration_limit_rad_s2=.2))
    class Client:
        protection_backend='minimal'
        def __init__(self,actual,mode,selected):
            assert actual is problem and mode=='hardware' and selected==list(ROBOT_IDS)
            self.problem=problem;self.positions=dict(plans[0]['request']['start'])
            self.protection_status=dict(warnings=['data unavailable'])
        def connect(self):pass
        def health(self):pass
        def wait_unpaused(self):pass
        def follow_group(self,trajectories,*,duration_s,segment):
            assert duration_s==2. and len(trajectories)==1
            arm=next(iter(trajectories));calls.append((arm,trajectories[arm]))
            self.positions.update(zip(joint_names(arm),trajectories[arm]['points'][-1]['positions']))
            segment['executed']=True
        def destroy_node(self):calls.append(('closed',None))
        stop=forbidden
    monkeypatch.setattr(minimal_execution,'MinimalHardwareClient',Client)
    monkeypatch.setattr(executor,'HardwareClient',forbidden)
    monkeypatch.setattr(executor,'_monitor',forbidden)
    monkeypatch.setattr(executor,'require_domain',lambda _:None)
    monkeypatch.setattr(executor,'HardwareProblem',lambda *a:problem)
    monkeypatch.setattr(executor,'motion_context',nullcontext)
    args=Box(plans=tmp_path/'plans',output=tmp_path/'output',sequence_sha256=digest,command_cap=.09,
             prepare_stopped_programs=False,area_session=None)
    executor.main(args)
    assert [arm for arm,_ in calls[:-1]]==list(ROBOT_IDS) and calls[-1][0]=='closed'
    assert [path for _,path in calls[:-1]]==[p['trajectory'] for p in plans]
    assert json.dumps(plans,sort_keys=True)==before
    result=json.loads((args.output/'sequence-result.json').read_text())
    assert result['complete'] and result['protection_backend']=='minimal'
    assert all(json.loads((args.output/('result-'+arm+'.json')).read_text())['command_limit_rad_s']==.09 for arm in ROBOT_IDS)
    # A changed frozen file still fails before any trajectory dispatch.
    file=tmp_path/'plans'/('0-'+ROBOT_IDS[0]+'.json')
    file.write_text(file.read_text()+' ')
    with pytest.raises(ValueError,match='plan file changed'):
        executor.checked_plans(tmp_path/'plans',digest,.09)


@pytest.mark.parametrize('interruption',[RuntimeError,KeyboardInterrupt])
def test_minimal_camera_failure_stops_only_for_explicit_operator_cancel(tmp_path,monkeypatch,interruption):
    digest=frozen_plans(tmp_path/'plans')
    _,plans=executor.checked_plans(tmp_path/'plans',digest,.09)
    calls=[]
    problem=Box(names={arm:joint_names(arm) for arm in ROBOT_IDS})
    class Client:
        protection_backend='minimal'
        def __init__(self,*a):
            self.problem=problem;self.positions=dict(plans[0]['request']['start']);self.protection_status={}
        def connect(self):pass
        def health(self):pass
        def wait_unpaused(self):pass
        def follow_group(self,*a,**k):raise interruption('test result')
        def stop(self):calls.append('pause_all');return dict(accepted=True)
        def destroy_node(self):pass
    monkeypatch.setattr(minimal_execution,'MinimalHardwareClient',Client)
    monkeypatch.setattr(executor,'_monitor',forbidden)
    output=tmp_path/'output';output.mkdir()
    args=Box(output=output,command_cap=.09,prepare_stopped_programs=False)
    with pytest.raises(RuntimeError,match='Sequence stopped'):
        executor.run_minimal_sequence(problem,plans,args,lambda:None)
    assert calls==(['pause_all'] if interruption is KeyboardInterrupt else [])


def test_minimal_camera_offline_input_needs_no_fictitious_native_modes(tmp_path,monkeypatch):
    state={joint:0. for arm in ROBOT_IDS for joint in joint_names(arm)}
    snapshot=dict(execution_mode='hardware',protection_backend='minimal',start=state,
                  source_records={arm:dict(q=[0.]*6) for arm in ROBOT_IDS})
    context=dict(config=dict(command_velocity_limit_rad_s=.1),modules={},canonical_collision_signature='geometry',mesh_sha256={})
    (tmp_path/'snapshot.json').write_text(json.dumps(snapshot))
    (tmp_path/'context.json').write_text(json.dumps(context))
    (tmp_path/'targets.yaml').write_text(yaml.safe_dump(dict(targets_rad={arm:[0.]*6 for arm in ROBOT_IDS})))
    problem=Box(description='<robot name="mock"/>',collision=Box(bounds={j:(-3.,3.) for j in state}),spheres=Box(geometry=Box(assets={})),plan=forbidden)
    monkeypatch.setattr(compiler,'HardwareProblem',lambda *a:problem)
    monkeypatch.setattr(compiler,'collision_signature',lambda _:'geometry')
    args=Box(output=tmp_path/'plans',context=tmp_path/'context.json',snapshot=tmp_path/'snapshot.json',targets=tmp_path/'targets.yaml',command_cap=.09)
    compiler.prepare(args)
    assert json.loads((args.output/'sequence.json').read_text())['segments']==[]


def test_camera_transfers_bind_same_candidate_as_ssh_working_directory(tmp_path,monkeypatch):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    monkeypatch.setenv('UWA_MINIMAL_RUNTIME','/home/rosmatch/minimal candidate')
    calls=[]
    monkeypatch.setattr(library,'logged_command',lambda command,*a,**k:calls.append(command))
    library.upload('setup/task/helper.py',tmp_path/'helper.py',tmp_path/'upload.log')
    library.download('setup/task/observations',tmp_path,tmp_path/'download.log')
    assert calls[0][-1]==library.N100_HOST+':/home/rosmatch/minimal candidate/setup/task/helper.py'
    assert calls[1][-2]==library.N100_HOST+':/home/rosmatch/minimal candidate/setup/task/observations'
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','legacy')
    assert library.remote_location('setup/task')==library.N100_HOST+':uwa-ur-runtime/setup/task'
