import pytest

from uwa_cell_control.count_comparison import compare_counts


def records():
    return [{'sample_id':f'fit_{i}','role':'fit','payload':[i]} for i in range(50)]+[
        {'sample_id':f'check_{i}','role':'validation','payload':[i]} for i in range(12)]


def test_nested_subsets_keep_identical_held_out_set_and_do_not_change_inputs():
    source=records();seen=[]
    def evaluate(selected):
        fit={r['sample_id'] for r in selected if r['role']=='fit'}
        held={r['sample_id'] for r in selected if r['role']=='validation'}
        assert held=={f'check_{i}' for i in range(12)} and not fit&held
        seen.append(fit)
        selected[0]['payload'][0]=-100
        return {'passed':True}
    result=compare_counts(source,[20,33,50],evaluate,seeds=[17,64])
    assert len(result['rows'])==5
    assert seen[0]<seen[2]<seen[4] and seen[1]<seen[3]<seen[4]
    assert source==records() and not result['changes_active_profile']
    assert len(result['validation_ids'])==12


def test_failed_subsets_are_reported_and_never_selected_as_a_profile():
    def fail(selected):raise ValueError('bad observation geometry')
    result=compare_counts(records(),[20,50],fail,seeds=[17])
    assert all(r['passed'] is False and 'geometry' in r['error'] for r in result['rows'])
    assert not result['changes_active_profile']
    with pytest.raises(ValueError,match='available'):compare_counts(records(),[51],fail)
    source=records();source[-1]['sample_id']=source[0]['sample_id']
    with pytest.raises(ValueError,match='Repeated'):compare_counts(source,[20],fail)
