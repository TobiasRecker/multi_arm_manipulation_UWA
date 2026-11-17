"""Episode teacher: explicit arm/table avoidance, unchanged rigid grasp model."""
import numpy as np
from scipy.spatial.transform import Rotation
from uwa_cell_motion.two_arm_teacher import TwoArmTeacher,point_box_distance,left_jacobian,pose_at
from uwa_cell_motion.object_transport import yaw_basis
from uwa_cell_motion.smooth_paths import progress,sample_segment


def control_map(s,controls):
    B=yaw_basis(s);C=np.eye(6);C[3:,3:]=left_jacobian((B@controls)[3:])
    return np.hstack([b*C for b in B])


def sphere_table_gap(points,radii,box_pose,half):
    local=(points-box_pose[:3,3])@box_pose[:3,:3]
    distance,normal=point_box_distance(local,half);gaps=distance-radii;i=int(np.argmin(gaps))
    return float(gaps[i]),i,box_pose[:3,:3]@normal[i]


class EpisodeTeacher(TwoArmTeacher):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.table_boxes=[b for b in self.environment_boxes if 'table' in b[0]]
        if not self.table_boxes:raise ValueError('No table geometry found')
        # Base/shoulder mounting contact is not a steering constraint. No FCL
        # exemptions are added. All distal arm, gripper and wrist-camera bodies
        # remain in this conservative sphere/table-box steering model.
        self.table_masks={a:np.array([any(x in link for x in ('upper_arm','forearm','wrist','robotiq'))
            for link in self.problem.spheres.links[a]]) for a in self.arms}
        if not all(mask.any() for mask in self.table_masks.values()):raise ValueError('Empty arm/table mask')

    def arm_table_gaps(self,pose,state,gradients=False):
        model=self.problem.spheres
        if gradients:world,jac=model.jacobians(state,self.arms);K,_=self.differential(pose,state)
        else:world=model.world(state)
        gaps=[];J=[]
        for arm in self.arms:
            mask=self.table_masks[arm];indices=np.flatnonzero(mask)
            for _,T,half in self.table_boxes:
                gap,i,n=sphere_table_gap(world[arm][mask],model.radii[arm][mask],T,half);gaps.append(gap)
                if gradients:J.append(n@jac[arm][indices[i]]@K)
        return (np.array(gaps),np.array(J)) if gradients else np.array(gaps)

    def path_rows(self,*args,gradients=False,**kwargs):
        rows=super().path_rows(*args,gradients=gradients,**kwargs)
        for row in rows:
            state=dict(self.start,**dict(zip(self.names,row['q'])))
            result=self.arm_table_gaps(np.array(row['pose']),state,gradients)
            row['arm_table_gaps_m']=(result[0] if gradients else result).tolist()
            if gradients:row['arm_table_gradient']=result[1]
        return rows

    def constraints(self,rows,controls,**kwargs):
        values,J=super().constraints(rows,controls,**kwargs);extra=[];grad=[]
        margin=kwargs.get('object_margin',.003)+kwargs.get('buffer',.001)
        for row in rows:
            extra.extend((np.array(row['arm_table_gaps_m'])-margin)/.05)
            grad.extend(row['arm_table_gradient']@control_map(row['s'],controls)/.05)
        return np.r_[values,extra],np.vstack([J,grad])

    def sample(self,trajectory,t):
        segment=trajectory['segment'];s=float(progress(segment['time_law'],t)[0])
        if not -1e-12<=s<=1+1e-12:raise ValueError('Progress outside rounding tolerance')
        s=float(np.clip(s,0,1));pose=pose_at(self.initial,trajectory['task'],s,trajectory['controls'])
        return pose,dict(self.start,**dict(zip(self.names,sample_segment(segment,t)))),s

    def validate(self,trajectory,**kwargs):
        result=super().validate(trajectory,**kwargs);dt=kwargs.get('dt',.005);minimum=float('inf');failures=[]
        for t in np.linspace(0,trajectory['duration_s'],int(np.ceil(trajectory['duration_s']/dt))+1):
            pose,state,s=self.sample(trajectory,float(t));gap=float(self.arm_table_gaps(pose,state).min());minimum=min(minimum,gap)
            if gap<.003-1e-8:failures.append(dict(time_s=float(t),s=s,reason='arm_table_margin',arm_table_gap_m=gap))
        result['min_arm_table_gap_m']=minimum;result['arm_table_failure_samples']=len(failures)
        result['failures'].extend(failures);result['passed']=bool(result['passed'] and not failures)
        return result

    def inspect(self,task,controls=None,count=121):
        result=super().inspect(task,controls,count)
        if result['complete']:
            rows=self.path_rows(task,controls,count=count)
            minimum=min(min(r['arm_table_gaps_m']) for r in rows)
            result['min_arm_table_gap_m']=minimum
            result['passed']=bool(result['passed'] and minimum>=.003)
        return result


def screen(p,task,count=41):
    """Cheap episode proposal filter; only final trajectory validation accepts."""
    state=dict(p.start);minimum=float('inf');table=float('inf');collisions=0
    from uwa_cell_motion.teacher_starts import state_check
    try:
        for s in np.linspace(0,1,count):
            pose=pose_at(p.initial,task,float(s),np.zeros((6,6)));state=p.solve(pose,state)
            collisions+=not p.full_check(pose,state)
            minimum=min(minimum,min(r['clearance_m'] for r in p.distances(pose,state)))
            table=min(table,float(p.arm_table_gaps(pose,state).min()))
        endpoint=state_check(p,pose,state);endtable=float(p.arm_table_gaps(pose,state).min())
        if not endpoint['passed'] or endtable<.004:
            return dict(eligible=False,status='ENDPOINT_INVALID',endpoint=endpoint,endpoint_table_gap_m=endtable)
        category='collision' if collisions or minimum<0 else 'near' if minimum<.08 or table<.02 else 'free'
        return dict(eligible=True,status='SCREENED',category=category,fcl_collision_samples=int(collisions),
            min_arm_gap_m=minimum,min_arm_table_gap_m=table,endpoint=endpoint,goal_state=state)
    except (ValueError,np.linalg.LinAlgError) as error:return dict(eligible=False,status='IK_FAILED',reason=str(error))
