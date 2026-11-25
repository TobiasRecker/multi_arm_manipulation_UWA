"""Contact review and finite force phases; all processes/devices are replaced."""
from contextlib import contextmanager
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import run_carton_cycle as cycle


def setup_case(tmp_path,monkeypatch,fail=None):
    monkeypatch.setenv('UWA_PROTECTION_BACKEND','minimal')
    entry=tmp_path/'entry';entry.mkdir()
    state=dict(segments=[dict(final_positions={'joint':0.})])
    (entry/'result.json').write_text(json.dumps(state))
    plan=tmp_path/'weigh-plan';plan.mkdir()
    (plan/'proof.json').write_text(json.dumps(dict(start={'joint':0.},duration_s=2.)))
    (plan/'review.json').write_text(json.dumps(dict(groups=[dict(arms=['right_front','right_rear'])])))
    report=dict(entry_state_sha256=cycle.file_sha256(entry/'result.json'),scene_session='session',
        motion_review='motion',entry_finished_unix=1.,
        weigh_plan=dict(path=str(plan),review_sha256=cycle.file_sha256(plan/'review.json')))
    calls=[]; approvals=[]
    class Flow:
        out=tmp_path
        def __init__(self):self.report=report
        @contextmanager
        def approval(self,store,meta,preview):
            approvals.append((meta,preview));yield 'contact-review'
        def phase(self,name,*args):
            calls.append(name)
            if fail==name:raise RuntimeError('finite task failure')
            if name=='close':
                (tmp_path/'grasp').mkdir()
                (tmp_path/'grasp/result.json').write_text(json.dumps(dict(success=True,gripper_commands_completed=True)))
            if name=='weigh':
                (tmp_path/'weighing').mkdir()
                (tmp_path/'weighing/result.json').write_text(json.dumps(dict(success=True,
                    phase='CARTON_LIFTED_AND_WEIGHED',weighing=dict(mass_kg=.8),measurement_available=True)))
    store=SimpleNamespace(status=lambda:dict(session_id='session',settings=dict(speed_percent=100/3)),
        export=lambda identifier:dict(preview=dict(start={},groups=[],duration_s=0)))
    monkeypatch.setattr(cycle,'entry_photo',lambda *args:dict(original_sha256='photo'))
    monkeypatch.setattr(cycle,'requested_program_starts',lambda *args:[])
    # New lift must request an explicit high-risk review regardless of old contact trust.
    monkeypatch.setattr(cycle,'assess_library_step',lambda *args,**kw:pytest.fail('New lift inherited old contact risk'))
    args=SimpleNamespace(entry_image=None,entry_metadata=None,start_ros_programs=False,risk=None,
        reason=None,visual_confirmed=True,config=Path('/unused/profile'))
    return Flow(),args,store,calls,approvals


def test_unloaded_reference_precedes_close_and_joint_lift_is_separate_review_component(tmp_path,monkeypatch):
    flow,args,store,calls,approvals=setup_case(tmp_path,monkeypatch)
    cycle.close_after_entry(flow,args,store)
    assert calls==['force_reference','close','force_supported','weigh']
    meta,preview=approvals[0]
    assert meta['stage']=='contact' and meta['risk']=='high'
    assert len(meta['components'])==2 and meta['components'][1]==flow.report['weigh_plan']['review_sha256']
    assert preview['groups'][0]['phase']=='weigh'
    assert flow.report['phase']=='CARTON_LIFTED_AND_WEIGHED'


@pytest.mark.parametrize('failure,expected',[
    ('force_reference',['force_reference']),('force_supported',['force_reference','close','force_supported'])])
def test_measurement_failure_does_not_close_early_open_release_or_move(tmp_path,monkeypatch,failure,expected):
    flow,args,store,calls,_=setup_case(tmp_path,monkeypatch,failure)
    with pytest.raises(RuntimeError):cycle.close_after_entry(flow,args,store)
    assert calls==expected


def test_changed_lift_is_rejected_before_reference_or_grasp(tmp_path,monkeypatch):
    flow,args,store,calls,_=setup_case(tmp_path,monkeypatch)
    (tmp_path/'weigh-plan/review.json').write_text('{}')
    with pytest.raises(ValueError,match='changed since'):cycle.close_after_entry(flow,args,store)
    assert not calls


@pytest.mark.parametrize('inner_knuckle_first',[False,True])
def test_nominal_contact_accepts_pads_but_never_exempts_inner_knuckles(inner_knuckle_first):
    import prepare_carton_weigh as planner
    flags={}
    class Model:
        bounds={arm+'_jaw':(0.,.8) for arm in planner.ARMS}
        scene=SimpleNamespace(allowed_collision_matrix=SimpleNamespace(set_entry=lambda a,b,v:flags.__setitem__(b,v)))
        def check(self,state,contacts=False):
            for arm in planner.ARMS:
                q=state.get(arm+'_jaw',0.)
                if inner_knuckle_first and q>=.1:return False,[]
                if q>=.2 and not all(flags.get(arm+f'_robotiq_85_{side}_finger_tip_link') for side in ('left','right')):
                    return False,[]
            return True,[]
    problem=SimpleNamespace(names={arm:['unused']*6+[arm+'_jaw'] for arm in planner.ARMS})
    if inner_knuckle_first:
        with pytest.raises(ValueError,match='not confined to the fingertip'):
            planner.nominal_pad_contact(Model(),problem,{},None)
    else:
        result=planner.nominal_pad_contact(Model(),problem,{},None)
        assert set(result)=={arm+'_jaw' for arm in planner.ARMS}
        assert all(abs(v-.2)<1e-7 for v in result.values())
    assert not any('inner_knuckle' in link for link in flags)


def test_catalog_exposes_weighing_step_when_configured(tmp_path,monkeypatch):
    import importlib.util
    repo=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('weigh_library',repo/'scripts/skill_library_server.py')
    library=importlib.util.module_from_spec(spec);spec.loader.exec_module(library)
    config=tmp_path/'live.json';config.write_text(json.dumps(dict(weigh_after_grasp=True)))
    runs=library.Runs(tmp_path/'runs',config)
    monkeypatch.setattr(runs,'camera_status',lambda:dict(calibrate_available=False,live_blocker='offline fixture'))
    carton=next(p for p in runs.catalog()['programs'] if p['id']=='carton-supported-v1')
    assert carton['stages'][-1]['id']=='weigh'
    assert '20mm higher' in carton['description']
    assert not carton['live_available']


@pytest.mark.parametrize('open_at_start',[False,True])
def test_approach_prepares_open_fingers_at_the_reviewed_required_boundary(tmp_path,monkeypatch,open_at_start):
    import time
    run=tmp_path/'cycle';run.mkdir();high=tmp_path/'prepared/high-plan';high.mkdir(parents=True)
    (high/'evidence.json').write_text(json.dumps(dict(open_right_grippers_required=open_at_start)))
    runners=[('high','high.py','--evidence',high),('entry','entry.py','--plan',tmp_path/'entry.json')]
    paths=[tmp_path/'review-high.json',tmp_path/'review-entry.json'];events=[];packets=[]
    class Flow:
        out=run
        report={}
        def save(self):pass
        @contextmanager
        def approval(self,store,meta,preview):packets.append(meta);yield 'review'
        def phase(self,name,tool,*args):
            events.append((name,list(args)))
            if '--output' in args:
                directory=Path(args[args.index('--output')+1]);directory.mkdir(parents=True,exist_ok=True)
                phase='ACTIVE_OPEN_HELD' if name=='prepare_grippers' else 'DONE'
                (directory/'result.json').write_text(json.dumps(dict(success=True,phase=phase)))
    store=SimpleNamespace(status=lambda:dict(area_released=True,area_released_at=time.time()-10,session_id='area',settings=dict(speed_percent=100/3)),check_active=lambda *args:None)
    monkeypatch.setattr(cycle,'current_capture',lambda *args:(None,None,{}))
    monkeypatch.setattr(cycle,'staged_approach',lambda *args:(runners,paths))
    monkeypatch.setattr(cycle,'requested_program_starts',lambda *args:[])
    monkeypatch.setattr(cycle,'motion_packet',lambda *args:(dict(components=['high-hash','entry-hash'],reason='fixture',stage='motion'),{}))
    args=SimpleNamespace(image=None,metadata=None,prepared_approach=tmp_path/'prepared',start_ros_programs=False,risk='high',reason='approved fixture')
    cycle.approach(Flow(),args,store)
    order=[name for name,_ in events]
    assert order==(['prepare_grippers','high','entry'] if open_at_start else ['high','prepare_grippers','entry'])
    preparation=next(values for name,values in events if name=='prepare_grippers')
    assert ('--current-planned-start' in preparation) is open_at_start
    assert preparation[preparation.index('--state')+1]==(high/'evidence.json' if open_at_start else run/'high/result.json')
    assert packets[0]['gripper_preparation']['before']==('high' if open_at_start else 'entry')
