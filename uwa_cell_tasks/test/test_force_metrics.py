import copy
import numpy as np
import pytest
from uwa_cell_tasks.force_metrics import contact_loads,analytic_upper_plane_force


def sample(a='floor',b='load',force=(1.,0.,3.)):
    return dict(collision1=a,collision2=b,points=[dict(position_world=[0.,0.,0.],
        normal_world=[0.,0.,1.],wrench_present=True,body1=dict(force=list(force)),body2=dict(force=[-x for x in force]))])


def test_reversed_duplicate_does_not_double_count_or_claim_body_direction():
    data=contact_loads([sample(),sample('load','floor')])
    assert data['unique_points']==1 and data['duplicate_points_removed']==1
    assert data['normal_load_n']==3 and data['tangential_load_n']==1
    assert data['raw_body_attribution_trusted'] is False
    np.testing.assert_allclose(analytic_upper_plane_force(data['points']),[1,0,3])


def test_distinct_pairs_and_reversed_normals_are_handled_separately():
    reverse=sample('load','floor',(-1.,0.,-3.));reverse['points'][0]['normal_world']=[0,0,-1]
    data=contact_loads([sample(),reverse,sample('other','load')])
    assert data['unique_points']==2 and data['duplicate_points_removed']==1
    assert data['normal_load_n']==6


def test_cached_manifold_geometry_does_not_double_count_impulse():
    cached=sample('load','floor');cached['points'][0]['position_world'][2]=.000001
    data=contact_loads([sample(),cached])
    assert data['unique_points']==1 and data['duplicate_points_removed']==1
    assert data['normal_load_n']==3


def test_missing_nonfinite_and_inconsistent_measurements_are_not_zero_force():
    bad=sample();bad['points'][0]['wrench_present']=False
    with pytest.raises(ValueError,match='missing'):contact_loads([bad])
    bad=sample(force=(float('nan'),0,0))
    with pytest.raises(ValueError,match='Malformed'):contact_loads([bad])
    bad=sample();bad['points'][0]['body2']['force']=[0,0,0]
    with pytest.raises(ValueError,match='inconsistent'):contact_loads([bad])
    bad=copy.deepcopy(sample());bad['points'][0]['body1']['force'][2]=4;bad['points'][0]['body2']['force'][2]=-4
    with pytest.raises(ValueError,match='Duplicate'):contact_loads([sample(),bad])
