#!/usr/bin/env python3
"""Read operator decisions and change carton pilot settings. Never sends robot goals."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import uuid

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "uwa_cell_tasks"))
from uwa_cell_tasks.motion_review import ReviewStore, TASK


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, help="Isolated store for mock/replay")
    commands = parser.add_subparsers(dest="command", required=True)
    modes = {name: commands.add_parser(name) for name in
             ("status", "export", "settings", "area", "decide", "reduce", "replay")}
    for command in modes.values():
        command.add_argument("--json", action="store_true", help="Machine-readable result (default)")
    for name in ("decide", "export"):
        modes[name].add_argument("--id", required=True)
    modes["decide"].add_argument("--sha256", required=True)
    modes["decide"].add_argument("--decision", required=True, choices=("approve", "reject", "replan"))
    modes["area"].add_argument("--state", required=True, choices=("release", "revoke"))
    modes["area"].add_argument("--session", required=True)
    modes["settings"].add_argument("--trust", type=int, choices=(0, 50, 100))
    for name in ("status", "settings"):
        modes[name].add_argument("--task", default=TASK, help="Task-specific trust setting")
    modes["settings"].add_argument("--speed-percent", type=float)
    modes["settings"].add_argument("--series-name")
    modes["settings"].add_argument("--series-min-percent", type=float)
    modes["settings"].add_argument("--end-series", action="store_true")
    modes["reduce"].add_argument("--series-name", required=True)
    modes["reduce"].add_argument("--speed-percent", required=True, type=float)
    for option in ("high-bundle", "entry-bundle"):
        modes["replay"].add_argument("--" + option, required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "replay" and (not args.store or args.store.resolve() ==
                                        (Path.home()/".local/state/uwa-motion-review").resolve()):
            raise ValueError("Replay requires a separate --store directory")
        store = ReviewStore(args.store)
        if args.command == "export":
            result = store.export(args.id)
        else:
            if args.command == "area":
                store.area(args.session, args.state == "release")
            elif args.command == "settings":
                store.settings(task=args.task, trust=args.trust, speed=args.speed_percent, series_name=args.series_name,
                               series_min=args.series_min_percent, end_series=args.end_series)
            elif args.command == "decide":
                store.decide(args.id, args.sha256, args.decision)
            elif args.command == "reduce":
                store.settings(speed=args.speed_percent, agent_series=args.series_name)
            elif args.command == "replay":
                from uwa_cell_tasks.carton_review import motion_packet, read_json
                speed = store.status()["settings"]["speed_percent"]
                dims = read_json(REPO/"uwa_cell_description/assets/carton_avocado_v1/asset.json")["dimensions_m"]
                meta, preview = motion_packet([args.high_bundle, args.entry_bundle], dims, speed,
                                             "high", "Archive replay for operator review.")
                meta["summary"] = "MOCK REPLAY — " + meta["summary"]
                meta["components"] = ["replay-only:" + sha for sha in meta["components"]]
                store.submit("mock-replay/" + uuid.uuid4().hex, meta, preview)
            result = store.status(getattr(args, "task", TASK))
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(json.dumps(dict(error=str(exc))))
        return 1
    print(json.dumps(result, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
