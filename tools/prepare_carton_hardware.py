#!/usr/bin/env python3
"""Prepare read-only real carton commissioning; no motion/activation commands."""
import argparse
import json
from pathlib import Path
import sys
# This workspace tool also runs before a package rebuild. Loading its own
# source package affects only this non-actuating process, not live task nodes.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'uwa_cell_tasks'))
from uwa_cell_tasks.hardware_preparation import prepare

if __name__ == '__main__':
    repo = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--profile', type=Path, default=repo/'uwa_cell_tasks/config/carton_hardware_first_test.yaml')
    p.add_argument('--inventory', type=Path, default=repo/'config/hardware_inventory.yaml')
    p.add_argument('--observe', action='store_true', help='Read native arm outputs and gripper GET registers; requires hardware domain66')
    a = p.parse_args()
    result = prepare(a.output, a.profile, a.inventory, live=a.observe)
    print(json.dumps(result, indent=2))
