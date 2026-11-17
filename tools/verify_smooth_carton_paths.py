#!/usr/bin/env python3
"""Independent timing reconstruction and denser full-scene geometry check."""
import argparse,hashlib,json,tempfile
from pathlib import Path
import numpy as np
from scipy.interpolate import make_interp_spline
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory');args=parser.parse_args()
root=Path(args.directory).resolve();r=json.loads((root/'result.json').read_text());raw=Path(r['source_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['source_sha256'];old=json.loads(raw);peaks=np.zeros(3);samples=0
for arm,path in r['paths'].items():
 assert abs(path['duration_s']-sum(s['time_law']['duration_s'] for s in path['segments']))<1e-10
 for source,s in zip(old['paths'][arm]['segments'],path['segments']):
  assert source['positions']==s['positions'] and source['knots']==s['knots']
  law=s['time_law'];tr=law['ramp_s'];tc=law['cruise_s'];v=law['peak_progress_speed'];T=law['duration_s'];assert abs(v*(tr+tc)-1)<1e-10;assert abs(2*tr+tc-T)<1e-10
  def profile(t):
   if t<=0:return [0.,0.,0.,0.]
   if t>=T:return [1.,0.,0.,0.]
   if t<tr:
    u=t/tr;return [v*tr*(2.5*u**4-3*u**5+u**6),v*(10*u**3-15*u**4+6*u**5),v/tr*(30*u*u-60*u**3+30*u**4),v/tr**2*(60*u-180*u*u+120*u**3)]
   if t<tr+tc:return [v*(.5*tr+t-tr),v,0.,0.]
   u=(t-tr-tc)/tr;return [v*(.5*tr+tc+tr*(u-2.5*u**4+3*u**5-u**6)),v*(1-10*u**3+15*u**4-6*u**5),-v/tr*(30*u*u-60*u**3+30*u**4),-v/tr**2*(60*u-180*u*u+120*u**3)]
  sp=make_interp_spline(s['knots'],s['positions'],k=1 if s['kind']=='JOINT' else 5)
  times=np.linspace(0,T,100001);x,xd,xdd,xddd=np.array([profile(t) for t in times]).T
  def d(n):return sp(x,nu=n) if n<=sp.k else np.zeros((len(x),6))
  values=[d(1)*xd[:,None],d(2)*xd[:,None]**2+d(1)*xdd[:,None],d(3)*xd[:,None]**3+3*d(2)*(xd*xdd)[:,None]+d(1)*xddd[:,None]]
  local=np.array([np.max(abs(a)) for a in values]);peaks=np.maximum(peaks,local)
  for i,key in enumerate(['velocity_rad_s','acceleration_rad_s2','jerk_rad_s3']):assert local[i]<=s['smooth_bounds'][key]+1e-8
  assert np.allclose(sp(0),s['positions'][0]) and np.allclose(sp(1),s['positions'][-1])
  for boundary in [0,tr,tr+tc,T]:
   assert np.allclose(profile(boundary-1e-8),profile(boundary+1e-8),atol=2e-6)
  samples+=len(times)
report=dict(status='PASS',samples=samples,independent_peaks=dict(zip(['velocity_rad_s','acceleration_rad_s2','jerk_rad_s3'],peaks.tolist())),statement='Same IK knots and endpoints; independently reconstructed time law; dense derivatives within analytical bounds; C3 ramp joins')
from uwa_cell_motion.carton_paths import CartonProblem
from uwa_cell_motion.common import config,joint_names,ROBOT_IDS
from uwa_cell_motion.smooth_paths import path_at
from itertools import combinations
from scipy.spatial.transform import Rotation
baseline=Path(r['source_path']).parent
binding=json.loads((baseline/'comparison.json').read_text());primitive=Path(binding['source_path']).parent
assert hashlib.sha256((primitive/'paths.json').read_bytes()).hexdigest()==binding['source_sha256']
with tempfile.TemporaryDirectory(prefix='uwa-smooth-independent-') as directory:
 p=CartonProblem(directory,config(primitive/'motion.yaml'),primitive/'layout.yaml')
 assert p.signature==r['model_signature'] and p.spheres.geometry.assets==r['mesh_sha256']
 mesh=p.carton['mesh_file'].parent/p.carton['manifest']['solid_mesh']
 assert hashlib.sha256(mesh.read_bytes()).hexdigest()==r['object_mesh_sha256']
 start=r['task']['start'];duration=max(v['duration_s'] for v in r['paths'].values())
 times=np.linspace(0,duration,int(np.ceil(duration/.005))+1);minimum=float('inf');max_step=0.;previous=None
 for t in times:
  state=dict(start)
  qgroup=np.concatenate([path_at(r['paths'][arm],float(t)) for arm in ROBOT_IDS])
  for i,arm in enumerate(ROBOT_IDS):state.update(zip(joint_names(arm),qgroup[6*i:6*i+6]))
  if previous is not None:max_step=max(max_step,float(np.max(abs(qgroup-previous))))
  previous=qgroup
  assert p.collision.check(state)[0],f'Full scene collision at {t}'
  world=p.spheres.world(state)
  for a,b in combinations(ROBOT_IDS,2):
   gap=float(p.spheres.nearest(world,a,b)['clearance_m']);minimum=min(minimum,gap)
   assert gap>=p.cfg['model_margin_m'],f'Pair margin at {t}'
 for arm,target in r['task']['targets'].items():
  actual=p.chains[arm].forward(state);wanted=np.asarray(target['tool0_target'])
  assert np.linalg.norm(actual[:3,3]-wanted[:3,3])<1e-4
  assert np.linalg.norm(Rotation.from_matrix(actual[:3,:3]@wanted[:3,:3].T).as_rotvec())<1e-3
  tcp=actual@target['tool0_to_tcp'];assert np.linalg.norm(tcp[:3,3]-target['tcp_world_m'])<1e-4
 assert max_step<=.005
 report['geometry']=dict(samples=len(times),max_time_step_s=float(times[1]-times[0]),min_pair_gap_m=minimum,max_joint_step_rad=max_step,
                         scope='Denser discrete FCL/all-six-pair check; same kinematics, not an independent physics model')
(root/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
