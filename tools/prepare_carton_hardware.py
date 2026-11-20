#!/usr/bin/env python3
"""Prepare read-only real carton commissioning; no motion/activation commands."""
import argparse
import json
from pathlib import Path
import sys
# This workspace tool also runs before a package rebuild. Loading its own
# source package affects only this non-actuating process, not live task nodes.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'uwa_cell_tasks'))
from uwa_cell_tasks.core import verify
from uwa_cell_tasks.hardware_preparation import prepare, validate_planning_snapshot

if __name__ == '__main__':
    repo = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--validate-planning-snapshot', type=Path,
                      help='Check a saved observations.json without connecting to hardware')
    p.add_argument('--profile', type=Path, default=repo/'uwa_cell_tasks/config/carton_hardware_first_test.yaml')
    p.add_argument('--inventory', type=Path, default=repo/'config/hardware_inventory.yaml')
    p.add_argument('--observe', action='store_true', help='Read native arm outputs and gripper GET registers; requires hardware domain66')
    p.add_argument('--stationarity-config',type=Path,help='Use the explicitly selected active guard profile for recorded quiet evidence; raw data retained')
    a = p.parse_args()
    if a.validate_planning_snapshot is not None:
        if a.observe or a.stationarity_config is not None:
            p.error('--validate-planning-snapshot reads an existing snapshot only')
        try:
            arms = validate_planning_snapshot(verify(json.loads(a.validate_planning_snapshot.read_text())))
        except (OSError, ValueError) as error:
            raise SystemExit(str(error)) from error
        result = dict(planning_ready=True, arms=arms, commands_sent=[])
    else:
        result = prepare(a.output, a.profile, a.inventory, live=a.observe,stationarity_config=a.stationarity_config)
    print(json.dumps(result, indent=2))
