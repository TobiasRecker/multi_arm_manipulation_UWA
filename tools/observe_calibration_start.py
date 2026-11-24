#!/usr/bin/env python3
"""Export the active model and current joints for camera-program planning.

Minimal mode reads the shared C++ state without stationarity or native-mode
tests. Legacy mode retains its separate RTDE observation. No robot writes.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET

from uwa_cell_motion.common import config, dump, joint_names, ROBOT_IDS
from uwa_cell_motion.guard_core import GuardState
from uwa_cell_motion.hardware_model import HardwareProblem
from uwa_cell_motion.hardware_state import RtdeStates, signature, require_domain
from uwa_cell_control.parallel_scan import collision_signature
from uwa_cell_tasks.motion_review import ReviewStore

MODULES = ['uwa_cell_motion.planning', 'uwa_cell_motion.hardware_model',
    'uwa_cell_motion.geometry', 'uwa_cell_motion.stopping_reserve', 'uwa_cell_motion.common',
    'uwa_cell_calibration.model', 'uwa_cell_control.scan_separation', 'uwa_cell_control.view_geometry']


def released_area(expected=None):
    status = ReviewStore().status()
    if not status['area_released'] or (expected and status['session_id'] != expected):
        raise RuntimeError('Release the work area in UWA Robot Power before starting capture setup.')
    if status['pending']:
        raise RuntimeError('Finish the active Motion review before starting capture setup.')
    return status


def observe(output):
    require_domain('hardware')
    status = released_area()
    from uwa_cell_motion.protection_backend import minimal_enabled
    minimal = minimal_enabled()
    runtime = Path.home()/'uwa-ur-runtime'
    if minimal:
        if os.environ.get('UWA_MINIMAL_RUNTIME'):
            runtime = Path(os.environ['UWA_MINIMAL_RUNTIME'])
        elif os.environ.get('UWA_MINIMAL_INSTALL'):
            runtime = Path(os.environ['UWA_MINIMAL_INSTALL']).parent
    repo = runtime / 'src/multi_arm_manipulation_UWA'
    cfg = config(repo / 'uwa_cell_motion/config/hardware_carton_supported_trend.yaml')
    output.mkdir(parents=True, exist_ok=True)
    problem = HardwareProblem(output / 'model-context', cfg, repo / 'config/hardware_inventory.yaml')
    tree = ET.fromstring(problem.description)
    for mesh in tree.iter('mesh'):
        path = Path(mesh.get('filename').removeprefix('file://'))
        mesh.set('filename', 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest())
    context = dict(config=cfg, inventory=problem.inventory, hardware_binding=problem.binding,
        hardware_signature=signature(problem, 'hardware'), model_signature=problem.signature,
        mesh_sha256=problem.spheres.geometry.assets,
        canonical_collision_signature=collision_signature(ET.tostring(tree, encoding='unicode')),
        modules={name: hashlib.sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest()
                 for name in MODULES})
    if minimal:
        from uwa_cell_tasks.minimal_snapshot import observe as shared_snapshot
        observation = shared_snapshot()
        if observation.get('model_signature') != problem.signature:
            raise ValueError('Shared C++ collision model differs from the observation planning model')
        records = {}
        start = {j:0. for names in problem.names.values() for j in names}
        for rid in ROBOT_IDS:
            sample = observation['arms'][rid]['samples'][-1]
            records[rid] = dict(q=sample['actual_q'], v=sample.get('actual_qd',[0.]*6),
                                device_stamp=sample['device_timestamp_s'],
                                received=sample['received_monotonic_s'])
            start.update(zip(joint_names(rid),sample['actual_q']))
        released_area(status['session_id'])
        dump(output/'snapshot.json',dict(schema_version=1,execution_mode='hardware',start=start,
            source_records=records,hardware_binding=problem.binding,protection_backend='minimal',
            source='Shared C++ actual joint snapshot; no stationarity or native-mode test',
            area_session=status['session_id'],
            tool_policy='unobserved fingers: full opening envelope; zero is a model coordinate'))
        dump(output/'model-context.json',context)
        return
    reader = RtdeStates(problem.profiles, cfg['state_timeout_s'])
    standstill = GuardState(cfg)
    try:
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            records, errors = reader.snapshot()
            now = time.monotonic()
            for rid, record in records.items():
                if standstill.last_stamp.get(rid) != record['device_stamp']:
                    standstill.receive(rid, record['q'], record['v'], record['device_stamp'], record['received'])
            if (set(records) == set(ROBOT_IDS) and not errors
                    and all(0 <= now-r['received'] <= cfg['state_timeout_s'] for r in records.values())
                    and all(standstill.stationary(rid, now) for rid in ROBOT_IDS)):
                break
            time.sleep(.02)
        else:
            raise RuntimeError('Fresh stationary joints are unavailable. Inspect UWA Robot Power → Safety log.')
        if any(r['status'] != dict(runtime_state=2, robot_mode=7, safety_mode=1) for r in records.values()):
            raise RuntimeError('All four URs must already be RUNNING / NORMAL / PLAYING. Prepare them in UWA Robot Power first; no automatic power or reset was sent.')
        released_area(status['session_id'])
        # Unobserved finger coordinates are model coordinates with full opening
        # envelopes, exactly as in the existing hardware snapshot CLI.
        start = {j: 0. for names in problem.names.values() for j in names}
        for rid, record in records.items():
            start.update(zip(joint_names(rid), record['q']))
        dump(output / 'snapshot.json', dict(schema_version=1, execution_mode='hardware', start=start,
            source_records=records, hardware_binding=problem.binding,
            source='output-only RTDE actual joints', area_session=status['session_id'],
            tool_policy='unobserved fingers: full opening envelope; zero is a model coordinate',
            stationarity={rid: standstill.stationarity_evidence(rid, now) for rid in ROBOT_IDS}))
        dump(output / 'model-context.json', context)
    finally:
        reader.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    observe(parser.parse_args().output)
