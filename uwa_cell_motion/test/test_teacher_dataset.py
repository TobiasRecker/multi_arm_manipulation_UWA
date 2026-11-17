from collections import Counter,defaultdict
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from uwa_cell_motion.teacher_dataset import (SCHEMA,atomic_json,digest,families,
    observation,pose_error,transitions)
from uwa_cell_motion.two_arm_teacher import pose_at,specification
from uwa_cell_motion.smooth_paths import plan_segment


def test_deterministic_families_and_no_variant_split_leakage():
    cases=families();assert cases==families()
    assert cases!=families(8)
    assert len({c['id'] for c in cases})==32
    assert Counter(c['category'] for c in cases)==dict(translation3d=8,rotation3d=8,mixed6d=16)
    assert Counter(c['split'] for c in cases)==dict(train=16,validation=8,test=8)
    splits=defaultdict(set);variants=Counter()
    for c in cases:splits[c['family']].add(c['split']);variants[c['family']]+=1
    assert all(len(s)==1 for s in splits.values())
    assert set(variants.values())=={2}
    for category in ('translation3d','rotation3d','mixed6d'):
        assert {c['split'] for c in cases if c['category']==category}=={'train','validation','test'}


def test_multiaxis_tasks_and_reference_categories():
    for c in families():
        t=c['task'];rot=np.array(t['rotation_vector_deg']);goal_rot=np.array(t['goal_rotation_vector_deg'])
        if c['category']=='translation3d':
            assert not np.any(rot) and not np.any(goal_rot)
        else:
            assert np.all(rot!=0) and np.all(goal_rot!=0)
            assert np.linalg.norm(np.cross(rot,goal_rot))>1
        if c['category']=='rotation3d':
            assert not np.any(t['goal_m']) and not np.any(t['excursion_m'])
        else:assert np.all(np.array(t['goal_m'])!=0) and np.all(np.array(t['excursion_m'])!=0)


def test_observation_uses_reference_and_distinguishes_same_goal_different_paths():
    initial=np.eye(4);initial[:3,:3]=Rotation.from_euler('xyz',[.2,.1,.6]).as_matrix()
    a=specification('a',excursion_m=[.1,.02,.03],rotation_deg=[20,30,10])
    b=specification('b',excursion_m=[-.1,.02,.03],rotation_deg=[-20,30,10])
    q=np.arange(12)*.01;pose=initial.copy();pose[0,3]=.01;s=.3
    x=observation(initial,a,pose,q,s);y=observation(initial,b,pose,q,s)
    assert x.shape==(SCHEMA['observation_size'],)
    assert np.allclose(x[:28],y[:28]) and not np.allclose(x[28:],y[28:])
    assert np.allclose(x[28:34],pose_error(pose_at(initial,a,s+.025,np.zeros((6,6))),pose))
    assert np.allclose(x[15:18],initial[:3,0]) and np.allclose(x[18:21],initial[:3,1])


def test_export_actions_reconstruct_next_pose_and_use_joint_interpolant():
    initial=np.eye(4);initial[:3,:3]=Rotation.from_euler('xyz',[.4,-.2,.5]).as_matrix()
    task=specification('mixed',[.08,-.03,.02],[25,-35,12],[.03,.02,.01],[5,8,-9])
    knots=np.linspace(0,1,11);positions=np.outer(knots,np.linspace(.01,.12,12))
    segment=plan_segment(dict(kind='OBJECT_DERIVED',knots=knots.tolist(),positions=positions.tolist(),check={}))
    trajectory=dict(task=task,controls=np.zeros((6,6)).tolist(),segment=segment,executable=False)
    rows=transitions(initial,trajectory)
    assert rows['observations'].shape==(100,52) and rows['actions'].shape==(100,6)
    assert rows['terminal'].sum()==1 and rows['terminal'][-1]
    assert np.allclose(rows['next_progress']-rows['progress'],.01)
    assert np.allclose(rows['q'],np.outer(rows['progress'],np.linspace(.01,.12,12)))
    for pose,target,action in zip(rows['object_pose'],rows['object_pose_next'],rows['actions']):
        assert np.allclose(pose[:3,3]+action[:3],target[:3,3])
        assert np.allclose(Rotation.from_rotvec(action[3:]).as_matrix()@pose[:3,:3],target[:3,:3])
    trajectory['executable']=True
    with pytest.raises(ValueError):transitions(initial,trajectory)


def runner():
    path=Path(__file__).resolve().parents[2]/'tools/generate_teacher_dataset.py'
    spec=importlib.util.spec_from_file_location('dataset_runner',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_resume_rejects_tampering_and_failed_case_not_exported(tmp_path):
    module=runner();cases=families()[:2];manifest=dict(cases=cases)
    (tmp_path/'cases').mkdir()
    failed=dict(case=cases[0],manifest_sha256=digest(manifest),status='REFERENCE_IK_FAILED')
    atomic_json(tmp_path/'cases'/f"{cases[0]['id']}.json",failed)
    done=module.load_completed(tmp_path,manifest);summary=module.summarize(tmp_path,manifest,done)
    assert summary['completed']==1 and summary['accepted']==0 and summary['transitions']==0
    import json
    assert json.loads((tmp_path/'train.json').read_text())['cases']==[]
    failed['manifest_sha256']='wrong'
    atomic_json(tmp_path/'cases'/f"{cases[0]['id']}.json",failed)
    with pytest.raises(ValueError,match='mismatch'):module.load_completed(tmp_path,manifest)


def test_resume_checks_accepted_export_hash(tmp_path):
    module=runner();case=families()[0];manifest=dict(cases=[case]);(tmp_path/'cases').mkdir()
    path=tmp_path/'cases/example.npz';path.write_bytes(b'original')
    result=dict(case=case,manifest_sha256=digest(manifest),status='VALIDATED',
                validation=dict(passed=True),export_validation=dict(passed=True),
                records_path='cases/example.npz',records_sha256=module.sha(path))
    atomic_json(tmp_path/'cases'/f"{case['id']}.json",result)
    assert len(module.load_completed(tmp_path,manifest))==1
    path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='modified'):module.load_completed(tmp_path,manifest)
