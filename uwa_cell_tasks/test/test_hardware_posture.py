"""Task elbow intent must describe geometry, not encoder winding sign."""
import numpy as np
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('hardware_posture',Path(__file__).resolve().parents[1]/'uwa_cell_tasks/hardware_posture.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
branch_allowed=module.branch_allowed


def test_elbow_branch_is_invariant_under_equivalent_encoder_turns():
    for winding in [-2*np.pi,0.,2*np.pi]:
        q=[0.,0.,-.8+winding,0.,0.,0.]
        assert branch_allowed(q,-1)
        assert not branch_allowed(q,1)
        q[2]=.8+winding
        assert not branch_allowed(q,-1)
        assert branch_allowed(q,1)


def test_task_policy_is_explicit_and_ambiguous_branch_is_not_approved():
    assert branch_allowed([0.]*6,None)
    assert not branch_allowed([0.]*6,-1)
