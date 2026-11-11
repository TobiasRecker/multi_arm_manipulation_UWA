"""Offline image-count experiment; never commands hardware or changes profiles."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import cv2
import numpy as np

from uwa_cell_calibration.storage import atomic_json
from .hardware_charuco import calibrate_intrinsics


def compare_counts(records,counts,evaluate,*,seeds=(17,64,101,302)):
    training=[r for r in records if r['role']=='fit']
    validation=[r for r in records if r['role']=='validation']
    identities=[r['sample_id'] for r in records]
    if len(set(identities))!=len(identities):raise ValueError('Repeated observation IDs')
    if len(training)+len(validation)!=len(records):raise ValueError('Unknown observation role')
    if len(validation)<6:raise ValueError('At least six held-out views required')
    counts=list(counts);seeds=list(seeds)
    if not seeds or not counts or len(set(counts))!=len(counts):raise ValueError('Provide unique counts and nonempty seeds')
    if any(type(n) is not int or not 20<=n<=len(training) for n in counts):
        raise ValueError('Counts must be between20 and the available fitting views')
    orders={seed:np.random.default_rng(seed).permutation(len(training)) for seed in seeds}
    rows=[]
    for count in counts:
        for seed in seeds[:1] if count==len(training) else seeds:
            selected=[training[i] for i in orders[seed][:count]]+validation
            row={'fit_count':count,'validation_count':len(validation),'seed':seed,
                 'fit_ids':[r['sample_id'] for r in selected if r['role']=='fit']}
            try:row.update(evaluate(deepcopy(selected)))
            except Exception as error:row.update(passed=False,error=str(error))
            rows.append(row)
    return {'schema_version':1,'counts':counts,'seeds':seeds,
            'validation_ids':[r['sample_id'] for r in validation],
            'purpose':'Report all sample-count subsets; held-out images never fit parameters',
            'changes_active_profile':False,'rows':rows}


def evaluate_subset(records,metadata,images):
    from uwa_cell_gazebo.charuco import detect_pose
    from uwa_cell_calibration.solver import solve_session
    intrinsics=calibrate_intrinsics(records,focus=records[0]['camera_settings']['focus'],
                                    image_size=records[0]['image_size'])
    rid=metadata['robot_id'];layout=metadata['layout'];observations=[]
    for record in records:
        pose=detect_pose(images[record['sample_id']],np.array(intrinsics['camera_matrix']),
            np.array(intrinsics['distortion']),layout['charuco'],layout['robots'][rid]['table'])
        if pose is None:raise ValueError(record['sample_id']+': image pose failed')
        observations.append(dict(record,T_camera_board=pose['T_camera_board'].tolist(),
            object_points=pose['object_points'],image_points=pose['image_points'],
            camera_matrix=intrinsics['camera_matrix'],distortion=intrinsics['distortion']))
    result=solve_session({rid:observations},bootstrap_count=0)['robots'][rid]
    return {'passed':result['passed'],'intrinsics_validation_median_px':float(np.median(intrinsics['validation_rms_px'])),
            'intrinsics_fit_rms_px':intrinsics['fit_rms_px'],'camera_matrix':intrinsics['camera_matrix'],
            'distortion':intrinsics['distortion'],'std_intrinsics':intrinsics['std_intrinsics'],
            'handeye_validation':result['validation'],'T_tool0_camera':result['T_tool0_camera'],
            'validation_samples':result['validation_samples'],
            'excluded_samples':result['excluded_samples']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--counts',default='20,33,50');parser.add_argument('--seeds',default='17,64,101,302')
    args=parser.parse_args();session=args.session.resolve();output=args.output.resolve()
    # A comparison cannot overwrite raw records, session metadata or result profiles.
    if output==session or output==session/'records' or session/'records' in output.parents:
        raise ValueError('Use a separate comparison output directory')
    output.mkdir(parents=True,exist_ok=True)
    metadata=json.loads((session/'session.json').read_text())
    records=[json.loads(p.read_text()) for p in sorted((session/'records').glob('sample_*.json'))]
    if any(r.get('accepted') is not True for r in records):raise ValueError('Inspect rejected observations before comparing')
    images={}
    for record in records:
        path=(session/'records'/record['image']).resolve()
        if path.parent!=session/'records':raise ValueError('Image must be in records directory')
        images[record['sample_id']]=cv2.imread(str(path))
        if images[record['sample_id']] is None:raise ValueError('Image unreadable: '+str(path))
    def evaluate(selected):
        result=evaluate_subset(selected,metadata,images)
        print(json.dumps({'fit_count':sum(r['role']=='fit' for r in selected),
                          'passed':result['passed'],'validation':result['handeye_validation']}),flush=True)
        return result
    result=compare_counts(records,[int(x) for x in args.counts.split(',')],evaluate,
                          seeds=[int(x) for x in args.seeds.split(',')])
    result.update(session=str(session),robot_id=metadata['robot_id'])
    atomic_json(output/'comparison.json',result)
    print(str(output/'comparison.json'),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
