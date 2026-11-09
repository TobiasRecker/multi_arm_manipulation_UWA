from concurrent.futures import Future
from itertools import product
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from uwa_cell_gazebo.configuration import load_layout,render_description,ROBOT_IDS,joint_names
from uwa_cell_calibration.model import CollisionModel
from uwa_cell_calibration.diagonal import prepare_schedule,coordinated_paths,DIAGONALS,ENVELOPE_MARGIN_M
from uwa_cell_calibration.backend import Backend


@pytest.fixture(scope='module')
def schedule(tmp_path_factory):
    directory=tmp_path_factory.mktemp('diagonal')
    layout=load_layout();model=CollisionModel(render_description(layout,directory)[0],directory)
    start={j:q for r in ROBOT_IDS for j,q in zip(joint_names(r),layout['robots'][r]['initial_positions'])}
    matrices={r:{'k':[[686.242218,0,320],[0,686.242218,240],[0,0,1]],'width':640,'height':480} for r in ROBOT_IDS}
    result=prepare_schedule(model,layout,start,matrices,list(ROBOT_IDS),30)
    return model,start,result


def test_inactive_arms_park_before_each_diagonal_and_all_original_poses_return(schedule):
    model,start,plan=schedule;state=dict(start);seen=[]
    for stage in plan['stages']:
        if stage['kind']=='measure':
            pair=stage['robots'];seen.append(tuple(pair))
            for rid in ROBOT_IDS:
                if rid not in pair:
                    np.testing.assert_allclose([state[j] for j in joint_names(rid)],plan['parking'][rid])
            assert all(c['envelope_separation_m']>=2*ENVELOPE_MARGIN_M for c in stage['certificates'])
            for rid in pair:
                poses=plan['plans'][rid]['poses']
                assert len(poses)==30 and sum(p['role']=='validation' for p in poses)==6
                state.update(zip(joint_names(rid),poses[-1]['joints']))
        else:
            assert model.check(state)[0]
            state.update(zip(joint_names(stage['robot']),stage['target']))
            assert model.check(state)[0]
    assert seen==list(DIAGONALS)
    assert state==start


def test_common_timing_and_independent_progress_including_one_arm_stopped(schedule):
    model,start,plan=schedule;state=dict(start)
    for stage in plan['stages']:
        if stage['kind']!='measure':
            state.update(zip(joint_names(stage['robot']),stage['target']));continue
        ids=stage['robots'];targets={r:plan['plans'][r]['poses'][0]['joints'] for r in ids}
        checked=coordinated_paths(model,state,targets)
        assert len({p[-1]['time'] for p in checked['paths'].values()})==1
        for path in checked['paths'].values():
            assert max(abs(v) for p in path for v in p['velocities'])<=.100001
            assert max(abs(v) for p in path for v in p['accelerations'])<=.200001
        paths=[checked['paths'][r] for r in ids]
        indices=[np.linspace(0,len(p)-1,9,dtype=int) for p in paths]
        for a,b in product(*indices):
            q=dict(state)
            for rid,path,index in zip(ids,paths,[a,b]):q.update(zip(joint_names(rid),path[index]['positions']))
            assert model.check(q)[0]
        break


def test_non_diagonal_pair_is_never_dispatched(schedule):
    model,start,plan=schedule
    with pytest.raises(ValueError,match='diagonal'):
        coordinated_paths(model,start,{r:[start[j] for j in joint_names(r)] for r in ['left_front','left_rear']})


def test_new_preparation_from_parked_poses_uses_board_reference_and_returns_to_measured_start(schedule):
    model,_,plan=schedule;layout=load_layout()
    start={j:q for r in ROBOT_IDS for j,q in zip(joint_names(r),plan['parking'][r])}
    ids=list(DIAGONALS[0]);matrices={r:{'k':[[686.242218,0,320],[0,686.242218,240],[0,0,1]],'width':640,'height':480} for r in ids}
    result=prepare_schedule(model,layout,start,matrices,ids,30)
    assert set(result['plans'])==set(ids)
    for rid in ids:
        positioning=next(s for s in result['stages'] if s['kind']=='positioning' and s['robot']==rid)
        np.testing.assert_allclose(positioning['target'],layout['robots'][rid]['initial_positions'])
    q=dict(start)
    for stage in result['stages']:
        if stage['kind']=='measure':
            for rid in stage['robots']:q.update(zip(joint_names(rid),result['plans'][rid]['poses'][-1]['joints']))
        else:q.update(zip(joint_names(stage['robot']),stage['target']))
    assert q==start


def test_close_swept_envelopes_fail_closed(schedule,monkeypatch):
    model,start,plan=schedule
    monkeypatch.setattr(model.arm_envelopes,'at_current_state',lambda rid:np.array([[0,0,0],[1,1,1]]))
    with pytest.raises(ValueError,match='envelopes too close'):
        coordinated_paths(model,start,{r:[start[j] for j in joint_names(r)] for r in DIAGONALS[0]})


def test_stop_cancels_both_handles_and_prevents_any_new_dispatch():
    cancelled=[];state={'phase':'MOVING'}
    def status(phase=None,**values):
        if phase:state['phase']=phase
        state.update(values)
    node=SimpleNamespace(motion_lock=threading.RLock(),pause=threading.Event(),abort=threading.Event(),
        shutdown_event=threading.Event(),state=state,running=True,status=status,
        motion_handles={r:SimpleNamespace(cancel_goal_async=lambda r=r:cancelled.append(r)) for r in DIAGONALS[0]},
        halt_thread=SimpleNamespace(is_alive=lambda:True))
    Backend.request_halt(node,'test stop')
    assert node.abort.is_set() and set(cancelled)==set(DIAGONALS[0])
    node.wait_unpaused=lambda:Backend.wait_unpaused(node)
    with pytest.raises(InterruptedError):Backend.move_many(node,{r:[0.]*6 for r in DIAGONALS[0]})


@pytest.mark.parametrize('rid',DIAGONALS[0])
def test_late_goal_acceptance_after_stop_is_cancelled_and_tracked_until_result(rid):
    result=Future();cancelled=[]
    handle=SimpleNamespace(accepted=True,get_result_async=lambda:result,cancel_goal_async=lambda:cancelled.append(rid))
    future=Future();future.set_result(handle)
    node=SimpleNamespace(motion_lock=threading.RLock(),motion_handles={},motion_results={},
        registration_pending={rid},halted=lambda:True,request_halt=lambda message:pytest.fail(message))
    Backend.accept_motion(node,rid,future)
    assert cancelled==[rid] and node.motion_handles[rid] is handle and not node.registration_pending
    result.set_result(None)
    assert not node.motion_handles


def test_transport_failure_does_not_treat_missing_acknowledgement_as_idle():
    future=Future();future.set_exception(RuntimeError('transport failed'))
    reasons=[]
    node=SimpleNamespace(uncertain_goals=set(),registration_pending={'left_front'},request_halt=reasons.append)
    Backend.accept_motion(node,'left_front',future)
    assert node.uncertain_goals=={'left_front'} and not node.registration_pending
    assert 'controller reset required' in reasons[0]
