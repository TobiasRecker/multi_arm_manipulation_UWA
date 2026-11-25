#!/usr/bin/env python3
"""Finite carton task measurements and one reviewed lift; never a force safety monitor."""
import argparse
import json
from pathlib import Path
import time
from uwa_cell_motion.common import config, dump
from uwa_cell_tasks.carton_weighing import ARMS, capture, estimate
from uwa_cell_tasks.reviewed_carton import file_hash, read_bundle, check_boundaries, START_TOLERANCE, speed_envelope

REPO = Path(__file__).resolve().parents[1]


def checked_plan(directory, profile):
    from uwa_cell_motion.hardware_model import HardwareProblem
    directory = directory.resolve(strict=True)
    proof = json.loads((directory/'proof.json').read_text())
    if (proof.get('phase') != 'OFFLINE_WEIGH_LIFT_PREPARED' or not proof.get('success')
            or proof.get('height_m') != .020):
        raise ValueError('Checked20mm lift proof required')
    for path, sha in proof['inputs'].items():
        if file_hash(path) != sha: raise ValueError('Weighing source changed: '+path)
    problem = HardwareProblem(directory/'execution-model', config(profile), REPO/'config/hardware_inventory.yaml')
    bundle = read_bundle(directory/'review.json', file_hash(directory/'review.json'), 'weigh',problem,directory/'proof.json',REPO/'tools')
    check_boundaries(bundle,proof['start'],proof['end'],list(ARMS))
    if len(bundle['groups'])!=1 or set(bundle['groups'][0]['arms'])!=set(ARMS):
        raise ValueError('A single common two-arm lift is required')
    return proof, bundle, problem


def measure(output):
    output.mkdir(parents=True,exist_ok=False)
    time.sleep(.5)  # Finite static task measurement after the normal controller result.
    result = capture(REPO/'config/hardware_inventory.yaml')
    result['success'] = True
    dump(output/'result.json',result)
    return result


def lift(args):
    from uwa_cell_motion.execution import motion_context
    from uwa_cell_motion.minimal_execution import MinimalHardwareClient
    from uwa_cell_motion.protection_backend import minimal_enabled
    from uwa_cell_tasks.motion_review import ReviewStore
    if not minimal_enabled():raise ValueError('This task extension is qualified only for the active minimal runtime')
    proof,bundle,problem = checked_plan(args.plan,args.config)
    if file_hash(args.plan/'review.json') != args.reviewed_sha256:raise ValueError('Lift differs from the contact review')
    reference = json.loads((args.reference/'result.json').read_text())
    supported = json.loads((args.supported/'result.json').read_text())
    store = ReviewStore(); store.check_active(args.review_id,args.reviewed_sha256,'contact')
    output = args.output.resolve(); output.mkdir(parents=True,exist_ok=False)
    report = dict(success=False,phase='REVIEWED_WEIGH_LIFT',mass_kg=None,measurement_available=False,
        review_id=args.review_id,reviewed_sha256=args.reviewed_sha256,segments=[],arm_commands=[],finger_commands=[])
    def save():dump(output/'result.json',report)
    save()
    group = bundle['groups'][0]
    envelope = speed_envelope(problem,ARMS,bundle['joint_limit_rad_s'],bundle['tcp_limit_m_s'])
    for arm,t in group['trajectories'].items():envelope.check_trajectory(arm,t['points'])
    with motion_context():
        client = MinimalHardwareClient(problem,'hardware',list(ARMS))
        try:
            client.connect(); client.wait_unpaused(); client.health()
            if any(j not in client.positions or abs(client.positions[j]-q)>START_TOLERANCE for j,q in group['start'].items()):
                raise ValueError('Lift start changed; replan, do not move from a new pose')
            store.begin_component(args.review_id,args.reviewed_sha256,'contact')
            segment = dict(arms=list(ARMS),executed=False); report['segments'].append(segment)
            report['arm_commands'].append(dict(arms=list(ARMS),bundle_sha256=args.reviewed_sha256));save()
            client.follow_group(group['trajectories'],duration_s=group['duration_s'],segment=segment)
            report.update(success=True,phase='CARTON_LIFTED_WEIGHING_UNAVAILABLE')
        except KeyboardInterrupt:
            report.update(error='Operator cancellation',phase='PAUSE_REQUESTED_BY_OPERATOR',stop_result=client.stop())
        except Exception as error:
            report.update(error=str(error),phase='LIFT_EXECUTION_FAILED')
        finally:
            report['final_positions']=dict(client.positions);save();client.destroy_node()
    if not report['success']:return 1
    try:
        lifted = measure(output/'lifted')
        result = estimate(reference,supported,lifted,proof['force_base_to_world'])
        report.update(weighing=result,mass_kg=result['mass_kg'],measurement_available=True,
                      phase='CARTON_LIFTED_AND_WEIGHED')
    except Exception as error:
        # A completed physical lift is never replayed or released due to a missing measurement.
        report['measurement_error']=str(error)
    save();return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('reference','supported','lift'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--config',type=Path,default=REPO/'uwa_cell_motion/config/hardware_carton_supported_trend.yaml')
    for name in ('plan','reference','supported'):parser.add_argument('--'+name,type=Path)
    for name in ('review-id','reviewed-sha256'):parser.add_argument('--'+name)
    args=parser.parse_args()
    if args.operation!='lift':measure(args.output);raise SystemExit(0)
    if not all((args.plan,args.reference,args.supported,args.review_id,args.reviewed_sha256)):
        parser.error('Lift needs its checked plan, two measurement windows and contact review')
    raise SystemExit(lift(args))
