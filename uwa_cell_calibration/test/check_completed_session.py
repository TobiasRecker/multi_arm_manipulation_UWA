"""Assert the complete 40-view-per-arm simulation acceptance criteria offline."""
import argparse,json
from pathlib import Path
from uwa_cell_calibration.storage import atomic_json,validate_result
from uwa_cell_gazebo.configuration import ROBOT_IDS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    plan=json.loads((args.session/'plan.json').read_text())
    result=json.loads((args.session/'result.json').read_text())
    truth=json.loads((args.session/'ground_truth_validation.json').read_text())
    validate_result(result)
    assert result['ground_truth_used_for_fit'] is False
    assert set(result['robots'])==set(ROBOT_IDS) and plan['samples_per_robot']==40
    report={'schema_version':1,'date':'2026-11-09','simulation_only':True,
            'samples_per_robot':40,'fit_per_robot':32,'validation_per_robot':8,
            'ground_truth_used_for_fit':False,'robots':{},'relative_bases':{}}
    for rid in ROBOT_IDS:
        files=sorted((args.session/rid).glob('sample_*.json'))
        samples=[json.loads(p.read_text()) for p in files]
        assert len(samples)==40
        assert sum(s['role']=='fit' for s in samples)==32
        assert sum(s['role']=='validation' for s in samples)==8
        assert len({s['candidate'] for s in samples})==40
        for path,sample in zip(files,samples):
            assert sample['corners']>=12 and sample['reprojection_rms_px']<=1
            assert sample['camera_info']['width']==640
            for suffix in ('_raw.png','_annotated.png'):assert path.with_name(path.stem+suffix).stat().st_size>0
        error=truth['robots'][rid]['handeye_error']
        assert error['translation_m']<=.003 and error['rotation_deg']<=.5
        report['robots'][rid]={'camera_error_mm':1000*error['translation_m'],
                               'camera_error_deg':error['rotation_deg'],
                               'validation':result['robots'][rid]['validation']}
    for table in ('left','right'):
        pair=result['relative_bases'][table];error=truth['relative_bases'][table]
        assert error['translation_m']<=.005 and error['rotation_deg']<=.5
        report['relative_bases'][table]={'distance_mm':pair['distance_mm'],
            'error_mm':1000*error['translation_m'],'error_deg':error['rotation_deg'],
            'distance_bootstrap_interval_mm':pair['distance_bootstrap_interval_mm']}
    report['passed']=True
    atomic_json(args.output,report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
