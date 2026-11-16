#!/usr/bin/env python3
"""Offline native-optics diagnostics. Never refits or activates calibration."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def radial_turns(distortion):
    k1, k2, _, _, k3 = distortion
    roots = np.polynomial.polynomial.polyroots([1., 3*k1, 5*k2, 7*k3])
    return sorted(float(np.sqrt(z.real)) for z in roots if abs(z.imag) < 1e-9 and z.real > 0)


def diagnose(job, camera, output):
    job, output = Path(job), Path(output)
    models_path = job/'prepared/camera_models.json'
    models = json.loads(models_path.read_text())
    selected = {k: v for k, v in models.items() if v['physical_camera'] == camera}
    if not selected:
        raise ValueError('No prepared camera views')
    first = next(iter(selected.values()))
    source = Path(first['source'])
    if hashlib.sha256(source.read_bytes()).hexdigest() != first['source_sha256']:
        raise ValueError('Calibration source changed since preparation')
    if len(first['D']) != 5:
        raise ValueError('This diagnostic supports Brown5 only')
    turns = radial_turns(first['D'])
    views = []
    for name, c in selected.items():
        xy = np.asarray(c['observation']['image_points'])
        record = json.loads((Path(c['image']).parent/'record.json').read_text())
        views.append(dict(view=name, image=c['image'], image_sha256=c['image_sha256'],
            captured_at=record.get('started_at'), board=c['source_board'],
            board_rms_native_px=c['board_rms_px'], corners=len(xy),
            observed_pixels_min=xy.min(0).tolist(), observed_pixels_max=xy.max(0).tolist(),
            metric_eligible=c['metric_eligible'], settings=record.get('settings_before'),
            identity=record.get('camera_identity', {}).get('uniqueCamId')))
    report = dict(camera=camera, source=str(source), source_sha256=first['source_sha256'],
        prepared_sha256=hashlib.sha256(models_path.read_bytes()).hexdigest(),
        K=first['K'], D=first['D'], image_size=first['image_size'], focus=first['focus'],
        calibration_passed_original=first['calibration_passed'],
        radial_positive_derivative_zero_radii=turns,
        radial_derivative_formula='1+3*k1*r^2+5*k2*r^4+7*k3*r^6; ideal normalized radius',
        radial_component_turn_is_not_full_2d_calibration_validation=True,
        views=views, hardware_queried=False, calibration_changed=False)
    output.mkdir(parents=True, exist_ok=False)
    (output/'diagnosis.json').write_text(json.dumps(report, indent=2)+'\n')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        r = np.linspace(0, .7, 500)
        k1, k2, _, _, k3 = first['D']
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        axes[0].plot(r, r*(1+k1*r*r+k2*r**4+k3*r**6))
        axes[0].set(xlabel='Ideal normalized radius r', ylabel='Radial distorted radius', title='Saved LF Brown5 radial component')
        axes[1].plot(r, 1+3*k1*r*r+5*k2*r**4+7*k3*r**6)
        axes[1].axhline(0, color='black', linestyle='--')
        axes[1].set(xlabel='Ideal normalized radius r', ylabel='Radial derivative', title='Non-monotone extrapolation')
        for ax in axes:
            ax.grid(True)
            for t in turns:
                if t < .7: ax.axvline(t, color='red', linestyle=':')
        fig.tight_layout();fig.savefig(output/'radial_extrapolation.png', dpi=150);plt.close(fig)
    except ImportError:
        pass
    print(json.dumps(dict(output=str(output), views=len(views), radial_turns=turns)))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job', type=Path, required=True)
    p.add_argument('--camera', default='left_front')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args();diagnose(a.job, a.camera, a.output)
