"""Carton preflight and real transfer builders stay bound to one N100 candidate.

Every process transport is mocked; no SSH, SCP, ROS or robot commands execute.
"""
import json
from pathlib import Path
import shlex
import sys

import pytest

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'tools'))
import run_carton_program as program


def mock_preflight(monkeypatch,remote_root):
    calls=[]
    checker=dict(components={'checked_planner':'same-source'})
    status=dict(area_released=True,pending=[],session_id='released-session')
    def command(args,log,timeout,**kwargs):
        calls.append((args,log,kwargs))
        if args[0]=='/usr/bin/ssh':
            return str(remote_root)+'\n'+json.dumps(status)+'\n'+json.dumps(checker)+'\n'
        return json.dumps(checker)
    monkeypatch.setattr(program,'logged_command',command)
    return calls,status


def test_actual_preflight_accepts_exact_candidate_and_builds_matching_remote_shell(tmp_path,monkeypatch):
    candidate=Path('/home/rosmatch/uwa-ur-runtime/minimal-candidates/minimal.test candidate')
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    monkeypatch.setenv('UWA_MINIMAL_RUNTIME',str(candidate))
    calls,status=mock_preflight(monkeypatch,candidate)
    root,actual_status,_=program.n100_preflight(tmp_path,program.PROGRAM)
    assert root==candidate and actual_status==status
    assert len(calls)==2
    shell=shlex.split(calls[0][0][-1])[2]
    assert 'cd -- '+shlex.quote(str(candidate))+'\n' in shell
    assert 'export UWA_MINIMAL_RUNTIME="$PWD"' in shell
    assert calls[0][2]['separate_stdout'] is True


def test_actual_preflight_refuses_other_candidate_before_local_checker(tmp_path,monkeypatch):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    monkeypatch.setenv('UWA_MINIMAL_RUNTIME','/home/rosmatch/minimal-candidate-a')
    calls,_=mock_preflight(monkeypatch,Path('/home/rosmatch/minimal-candidate-b'))
    with pytest.raises(ValueError,match='Unexpected N100 runtime workspace'):
        program.n100_preflight(tmp_path,program.PROGRAM)
    assert len(calls)==1


@pytest.mark.parametrize('backend',['legacy','minimal'])
def test_actual_preflight_preserves_default_runtime_when_no_candidate(tmp_path,monkeypatch,backend):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND',backend)
    monkeypatch.delenv('UWA_MINIMAL_RUNTIME',raising=False)
    calls,_=mock_preflight(monkeypatch,Path('/home/rosmatch/uwa-ur-runtime'))
    root,_,_=program.n100_preflight(tmp_path,program.PROGRAM)
    assert root==Path('/home/rosmatch/uwa-ur-runtime') and len(calls)==2
    calls,_=mock_preflight(monkeypatch,Path('/home/rosmatch/unexpected-runtime'))
    with pytest.raises(ValueError,match='Unexpected N100 runtime workspace'):
        program.n100_preflight(tmp_path,program.PROGRAM)


def test_actual_upload_and_frozen_approach_transfer_use_candidate_destinations(tmp_path,monkeypatch):
    candidate=Path('/home/rosmatch/minimal candidate')
    remote='setup/tasks/test-run'
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    monkeypatch.setenv('UWA_MINIMAL_RUNTIME',str(candidate))
    calls=[]
    def command(args,*unused,**kwargs):
        calls.append(args)
        if 'stage_carton_plan.py' in str(args):
            prepared=Path(args[args.index('--output')+1])
            prepared.mkdir(parents=True)
            (prepared/'bound-plan.json').write_text('{}')
        return ''
    monkeypatch.setattr(program,'logged_command',command)
    image=tmp_path/'photo.png';image.write_bytes(b'photo')
    metadata=tmp_path/'metadata.json';metadata.write_text('{}')
    intrinsics=tmp_path/'intrinsics.json';intrinsics.write_text('{}')
    program.upload(remote+'/entry/',image,tmp_path/'entry.log',metadata)
    assert calls[-1][-1]==f'{program.N100_HOST}:{candidate}/{remote}/entry/'
    assert calls[-1][-3:-1]==[image,metadata]
    options=program.transfer_approach(remote,candidate,tmp_path/'plan',image,metadata,
                                     dict(intrinsics=intrinsics),tmp_path,None)
    assert options==[]
    staging=calls[-2]
    assert Path(staging[staging.index('--target-root')+1])==candidate/remote/'prepared'
    assert Path(staging[staging.index('--target-workspace')+1])==candidate
    assert calls[-1][0]=='/usr/bin/scp' and '-r' in calls[-1]
    assert calls[-1][-1]==f'{program.N100_HOST}:{candidate}/{remote}/'
    assert (tmp_path/'handoff/input/standard.png').read_bytes()==b'photo'


@pytest.mark.parametrize('payload',['../escape','setup/../escape','/absolute/target',''])
def test_payload_traversal_is_rejected_before_upload_transport(tmp_path,monkeypatch,payload):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    monkeypatch.setenv('UWA_MINIMAL_RUNTIME','/home/rosmatch/minimal')
    calls=[]
    monkeypatch.setattr(program,'logged_command',lambda *a,**k:calls.append(a))
    with pytest.raises(ValueError,match='relative path without traversal'):
        program.upload(payload,tmp_path/'file',tmp_path/'log')
    assert not calls


def test_candidate_path_validation_prevents_any_transport(tmp_path,monkeypatch):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    monkeypatch.setenv('UWA_MINIMAL_RUNTIME','relative/candidate')
    calls=[]
    monkeypatch.setattr(program,'logged_command',lambda *a,**k:calls.append(a))
    with pytest.raises(ValueError,match='absolute'):
        program.n100_preflight(tmp_path,program.PROGRAM)
    with pytest.raises(ValueError,match='absolute'):
        program.upload('setup/task/file',tmp_path/'file',tmp_path/'log')
    assert not calls


def test_legacy_upload_target_ignores_inactive_candidate_setting(tmp_path,monkeypatch):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','legacy')
    monkeypatch.setenv('UWA_MINIMAL_RUNTIME','/home/rosmatch/inactive-candidate')
    calls=[]
    monkeypatch.setattr(program,'logged_command',lambda command,*a,**k:calls.append(command))
    program.upload('setup/task/entry/',tmp_path/'image',tmp_path/'log')
    assert calls[0][-1]==f'{program.N100_HOST}:uwa-ur-runtime/setup/task/entry/'
