#!/usr/bin/env python3
"""Execute a single reviewed finite air trial; no new protection services."""
import argparse
import hashlib
import json
from pathlib import Path
import time

try:
    from air_review_store import ReviewStore
except ModuleNotFoundError:
    from uwa_cell_tasks.motion_review import ReviewStore
try:
    from return_home_helpers import approval,check_start,follow_loaded,follow_unloaded
except ModuleNotFoundError:
    from execute_return_home import approval,check_start,follow_loaded,follow_unloaded
from return_home_model import model_identity
from uwa_cell_motion.common import config,dump
from uwa_cell_motion.execution import motion_context
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.minimal_execution import MinimalHardwareClient
from uwa_cell_tasks.carton_review import entry_photo
from uwa_cell_tasks.reviewed_carton import check_boundaries,speed_envelope

ROOT=Path('src/multi_arm_manipulation_UWA')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())


def completion_ack(client,arms):
    """Consume the terminal status of our own successful action before handoff.

    This finite protocol step uses existing subscriptions, with no extra RPC,
    periodic watcher, stationary test, speed change or global stop.
    """
    client.wait(lambda:all(not (client.protection_status or {}).get('arms',{}).get(a,{}).get('action_active')
        for a in arms),timeout=3.)


def run(args):
    plan=read(args.plan)
    if sha(args.plan)!=args.sha256 or plan.get('kind')!='carton_air_demo' or plan.get('version')!=1:
        raise ValueError('Exact frozen air-trial plan required')
    path=args.plan.parent/'execution.json'
    if path.exists():raise ValueError('This air trial has already been attempted')
    result=dict(success=False,plan_sha256=args.sha256,physical_tool=False,segments=[],finger_commands={})
    def save():dump(path,result)
    save();store=ReviewStore()
    try:
        status=store.status('carton_supported_grasp')
        if (not status['area_released'] or status['session_id']!=args.session
                or status['settings']['speed_percent']!=plan['speed_percent']):
            raise ValueError('Work area or task speed changed')
        p=HardwareProblem(args.plan.parent/'native-model',
            config(ROOT/'uwa_cell_motion/config/hardware_carton_supported_trend.yaml'),ROOT/'config/hardware_inventory.yaml')
        if model_identity(p)!=plan['model_identity']:
            raise ValueError('Native cell model differs from the qualified air trial')
        groups=plan['phases'];selected=sorted({a for g in groups for a in g['arms']})
        envelope=speed_envelope(p,selected,.1,1/12)
        check_boundaries(dict(start=plan['start'],groups=groups),plan['start'],plan['end'],selected)
        for group in groups:
            for arm,trajectory in group['trajectories'].items():envelope.check_trajectory(arm,trajectory['points'])
        # Show the actual new held carton, acquired after the completed lift.
        photo=entry_photo(args.photo,args.metadata,args.after_lift,time.time())
        preview=dict(plan['preview'],image=photo)
        component=hashlib.sha256((args.sha256+'/'+photo['original_sha256']).encode()).hexdigest()
        meta=dict(task='carton_supported_grasp',stage='motion',risk='high',
            summary='Carton drawing trial · empty worker gripper',
            reason='Both right arms carry and turn the empty carton. Left front follows the rehearsed house, circle and six virtual drilling cycles with an empty gripper; left rear parks. No physical tool, contact drawing or drilling. The complete hardware sequence and camera-holder obstacle have been checked offline. First real large coupled rotations; the model proof is not a measured synchronization or grip-strength guarantee.',
            arms=selected,components=[component],duration_s=plan['duration_s'],speed_percent=plan['speed_percent'],
            joint_limit_rad_s=.1,scene_session=args.session,requires_area=True,capture_sha256=photo['original_sha256'])
        with approval(store,'carton-air/'+args.plan.parent.name+'/'+args.sha256,meta,preview) as ticket:
            with motion_context():
                client=MinimalHardwareClient(p,'hardware',selected)
                try:
                    client.connect();check_start(client,plan['start'],selected)
                    store.begin_component(ticket,component,'motion')
                    for group in groups:
                        store.check_active(ticket,component,'motion');check_start(client,group['start'],group['arms'])
                        segment=dict(phase=group['phase'],arms=group['arms'],executed=False)
                        result['segments'].append(segment);save()
                        print('AIR_PHASE '+json.dumps(dict(phase=group['phase'],state='running',duration_s=group['duration_s'])),flush=True)
                        if len(group['arms'])>1:follow_loaded(client,group,segment)
                        else:follow_unloaded(client,group,segment)
                        completion_ack(client,group['arms']);save()
                        print('AIR_PHASE '+json.dumps(dict(phase=group['phase'],state='done')),flush=True)
                finally:client.destroy_node()
        result.update(success=True,phase='CARTON_AIR_TRIAL_COMPLETED',completed_at=time.time())
    except BaseException as error:
        result['error']=str(error)or'Interrupted';raise
    finally:save()
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','photo','metadata'):parser.add_argument('--'+name,type=Path,required=True)
    for name in ('sha256','session'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--after-lift',type=float,required=True)
    args=parser.parse_args();args.plan=args.plan.resolve();print(json.dumps(run(args)))
