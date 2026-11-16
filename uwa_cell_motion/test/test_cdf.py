from pathlib import Path
import json
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]))
from uwa_cell_motion.common import config,nominal_state,joint_names
from uwa_cell_motion.planning import Problem
from uwa_cell_motion.cdf_geometry import FrozenScene
from uwa_cell_motion.cdf import ContactBank,build_bank,qp_step,plan,rollout


@pytest.fixture(scope='module')
def problem(tmp_path_factory):return Problem(tmp_path_factory.mktemp('cdf-model'),config())


def request(problem,rid='right_rear'):
    start=nominal_state(problem.layout);q=np.array([start[j] for j in joint_names(rid)])
    return problem.normalize(dict(start=start,goals={rid:(q+.01).tolist()}))


@pytest.mark.parametrize('rid',['left_front','left_rear','right_front','right_rear'])
def test_batched_ur_fk_matches_full_cell_including_fixed_tools(problem,rid):
    r=request(problem,rid);scene=FrozenScene(problem,r);rng=np.random.default_rng(72)
    qs=rng.uniform(scene.bounds[:,0],scene.bounds[:,1],(5,6));centres=scene.forward(qs)[0]
    for q,points in zip(qs,centres):
        expected=problem.spheres.world(problem.state(r,q))[rid][scene.indices]
        assert np.allclose(points,expected,atol=1e-10,rtol=0)


def test_scene_sdf_gradient_matches_finite_difference_at_nonconstant_contacts(problem):
    scene=FrozenScene(problem,request(problem));rng=np.random.default_rng(91);checked=0
    for q in rng.uniform(scene.bounds[:,0],scene.bounds[:,1],(40,6)):
        d,g,k=scene.sdf(q)
        if np.linalg.norm(g)<1e-5:continue
        epsilon=1e-6
        numeric=np.array([(scene.sdf(q+np.eye(6)[i]*epsilon)[0][0]-scene.sdf(q-np.eye(6)[i]*epsilon)[0][0])/(2*epsilon) for i in range(6)])
        assert np.allclose(g[0],numeric,rtol=1e-4,atol=1e-6)
        assert np.all(g[0,k[0]:]==0);checked+=1
    assert checked>=10


def test_cdf_uses_joint_radians_prefixes_and_unit_analytic_gradient():
    bank=ContactBank([[0,0,9,9,9,9],[2,2,0,0,0,0]],[2,6],{})
    q=np.array([.3,.4,1,2,3,4.]);d,g,i=bank.query(q)
    assert d==pytest.approx(.5) and i==0 and np.allclose(g,[.6,.8,0,0,0,0])
    assert np.linalg.norm(g)==pytest.approx(1)
    assert bank.query(q+[0,0,10,-20,30,10])[0]==pytest.approx(d)
    assert np.allclose(q-d*g,[0,0,1,2,3,4])
    assert np.allclose(bank.query([0,0,1,2,3,4])[1],0)


def test_cdf_min_fusion_and_gradient_match_numerical_distance():
    bank=ContactBank([[1,0,0,0,0,0],[-1,0,0,0,0,0]],[6,6],{})
    q=np.array([.2,.2,.1,0,0,0]);d,g,i=bank.query(q);assert i==0
    numeric=np.array([(bank.query(q+np.eye(6)[i]*1e-6)[0]-bank.query(q-np.eye(6)[i]*1e-6)[0])/2e-6 for i in range(6)])
    assert np.allclose(g,numeric,atol=1e-7)


def test_bank_requires_exact_frozen_state_tools_and_model(problem,tmp_path):
    r=request(problem);scene=FrozenScene(problem,r);bank=ContactBank([[0]*6],[6],{'scene_binding':scene.binding});path=tmp_path/'bank.npz';bank.save(path)
    assert ContactBank.load(path,scene).digest==bank.digest
    r['start'][joint_names('left_rear')[0]]+=.01
    with pytest.raises(ValueError,match='frozen obstacle'):ContactBank.load(path,FrozenScene(problem,r))
    r=request(problem);r['start'][problem.names['right_rear'][6]]+=.1
    with pytest.raises(ValueError,match='frozen obstacle'):ContactBank.load(path,FrozenScene(problem,r))


def test_single_arm_only_and_hardware_not_supported(problem):
    r=request(problem);r['selected'].append('left_front')
    with pytest.raises(ValueError,match='exactly one'):FrozenScene(problem,r)
    with pytest.raises(ValueError,match='hardware not supported'):plan(SimpleNamespace(inventory='hardware'),{},None)


def test_log_qp_enforces_avoidance_while_respecting_joint_bounds():
    q=np.zeros(6);target=np.ones(6);gradient=np.array([-1.,0,0,0,0,0]);bounds=np.tile([-1.,1.],(6,1))
    delta,error=qp_step(q,target,gradient,.07,bounds,max_step=.05,gamma=.9)
    assert error is None and delta[0]<0 and np.max(abs(delta))<=.05000001
    assert np.log(.97)+gradient@delta>=-1e-7
    assert delta[1]>.0499
    delta,error=qp_step(q,target,gradient,0,bounds,max_step=.01,gamma=.9)
    assert delta is None and error.startswith('QP_INFEASIBLE')


def test_diagonal_qp_solution_matches_independent_normalized_scipy_oracle():
    from scipy.optimize import minimize
    rng=np.random.default_rng(26);weights=np.array([150.,190.,80.,70.,70.,90.])/190;ridge=.01/190
    bounds=np.tile([-.2,.2],(6,1));q=np.zeros(6)
    for _ in range(15):
        target=rng.normal(0,.2,6);g=rng.normal(0,1,6);g/=np.linalg.norm(g);limit=np.log(.97)
        x,error=qp_step(q,target,g,.07,bounds,max_step=.2,gamma=.9);assert error is None
        def cost(z):return np.sum(weights*(z-target)**2)+ridge*np.dot(z,z)
        oracle=minimize(cost,np.where(g>=0,.2,-.2),method='SLSQP',bounds=bounds,
            constraints=[dict(type='ineq',fun=lambda z:limit+g@z)],options=dict(ftol=1e-12,maxiter=100))
        assert oracle.success and np.allclose(x,oracle.x,atol=3e-6,rtol=0)


def test_feasible_ur_case_that_previously_false_failed_in_generic_solver():
    q=np.array([.6950647762018488,-.6239783205346316,-1.4831945750486633,-.6218552308276214,1.1525423096249219,.775703649600223])
    target=np.array([2.1355714010375704,-1.7208839619288236,-.23616303797525373,-.6926386868269171,.8783970110208525,.22671520250242871])
    g=np.array([-.9617339933885325,.27398490097256467,0,0,0,0]);distance=.0682077271257505
    delta,error=qp_step(q,target,g,distance,np.tile([-2*np.pi,2*np.pi],(6,1)))
    assert error is None and np.log(distance+.9)+g@delta>=-1e-9
    assert delta[0]<0 and max(abs(delta))<=.040000001


def test_reactive_rollout_does_not_fall_back_to_rrt_when_validation_blocks():
    p=SimpleNamespace(cfg={'goal_tolerance_rad':.001},edge=lambda *a,**k:False)
    r={'start':{str(i):0 for i in range(6)},'joint_names':[str(i) for i in range(6)],'target':[1]*6}
    scene=SimpleNamespace(bounds=np.tile([-2.,2.],(6,1)),sdf=lambda q:(np.array([1.]),None,None))
    bank=ContactBank([[-2]*6],[6],{})
    path,error,trace=rollout(p,r,scene,bank,1.)
    assert path is None and error.startswith('STUCK: full-cell') and len(trace)==1


def test_real_ur_multistart_contacts_and_cache_validation(problem,tmp_path):
    source=Path(__file__).parents[1]/'config/benchmark_suite_20261113.json'
    case=next(c for c in json.loads(source.read_text())['cases'] if c['id']=='blocked_direct_04')
    r=problem.normalize(case['request']);scene=FrozenScene(problem,r)
    bank=build_bank(scene,r,samples=128,seed=0,budget_s=30.)
    residual,_,depth=scene.sdf(bank.contacts)
    assert len(bank.contacts)>=3 and np.max(abs(residual))<=.001 and np.array_equal(depth,bank.depth)
    assert np.all(bank.contacts>=scene.bounds[:,0]) and np.all(bank.contacts<=scene.bounds[:,1])
    bank.save(tmp_path/'contacts.npz');assert ContactBank.load(tmp_path/'contacts.npz',scene).digest==bank.digest
    # A different active-arm start reuses the same frozen scene; no fabricated
    # states for the other arms or gripper are introduced in a successful plan.
    free=request(problem);result=plan(problem,free,bank)
    assert result['success'] and result['simulation_only'] and result['method']=='cdf'
    assert result['metrics']['full_cell_collision_checked']
    for point in result['trajectory']['points']:
        state=problem.state(result['request'],point['positions'])
        assert all(state[j]==free['start'][j] for rid,names in problem.names.items() if rid!='right_rear' for j in names)


@pytest.mark.parametrize('contacts,depth',[([],[]),([[float('nan')]*6],[6]),([[0]*6],[0])])
def test_invalid_banks_are_not_silently_clear(contacts,depth):
    with pytest.raises(ValueError):ContactBank(contacts,depth,{})
