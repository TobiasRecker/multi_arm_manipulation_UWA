#!/usr/bin/env python3
"""File-only cooperative drawing pilot, execution summary and scoped feedback."""
import argparse
import json
from pathlib import Path
import sys

# The pilot is a source-tree tool; adding it must not reinstall shared native
# contact plugins while other simulations may still use their pinned binaries.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'uwa_cell_tasks'))
from uwa_cell_tasks.pilot_episode import Episode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('run')
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    recipe = p.add_mutually_exclusive_group()
    recipe.add_argument('--variant',choices=('baseline','overlap','closer_coordinated','away_face'),default='baseline')
    recipe.add_argument('--faces', nargs='+', help='Search presentations for the given ordered box faces')
    p.add_argument('--radius-mm', type=float, help='Circle radius for --faces (default 25)')
    p.add_argument('--presentation-budget', type=int, help='Maximum pose candidates per face (default 8)')
    p.add_argument('--max-transfer-s', type=float, help='Reject any presentation over this model time')
    p.add_argument('--feedback-from',type=Path)
    p = sub.add_parser('summary')
    p.add_argument('run', type=Path)
    p = sub.add_parser('history')
    p.add_argument('root', type=Path, help='Directory containing separate pilot runs')
    p = sub.add_parser('feedback')
    p.add_argument('run', type=Path)
    choice = p.add_mutually_exclusive_group(required=True)
    choice.add_argument('--text')
    choice.add_argument('--file', type=Path, help='JSON exported by the viewer')
    p.add_argument('--phase', default='overall')
    args = parser.parse_args()
    if args.command == 'run':
        from uwa_cell_tasks.box_drawing import compile_pilot
        try:
            result = compile_pilot(
                args.source, args.output, variant=args.variant, feedback_from=args.feedback_from,
                faces=args.faces, radius_m=None if args.radius_mm is None else args.radius_mm/1000,
                presentation_budget=args.presentation_budget, max_transfer_s=args.max_transfer_s)
        except (ValueError, OSError) as error:
            parser.exit(1, f'box_drawing_pilot: {error}\n')
        print(json.dumps(dict(status=result['status'], output=str(args.output.resolve()),
                              validation=result['validation']), indent=2))
    elif args.command == 'history':
        rows = []
        for path in sorted(args.root.glob('*/episode/episode.json')):
            episode = Episode(path.parent)
            summary = episode.summary()
            rows.append(dict(run=str(path.parent.parent), backend=summary['backend'],
                             status=summary['status'], model_duration_s=summary['model_duration_s'],
                             terminal_phase=summary['terminal_phase'],
                             terminal_details=summary['terminal_details'],
                             feedback=[dict(phase=r['phase'], text=r['details']['text']) for r in summary['feedback']],
                             interventions=summary['detected_events']['agent_intervention'],
                             last_event_sha256=summary['last_event_sha256']))
        print(json.dumps(rows, indent=2))
    else:
        episode = Episode(args.run / 'episode')
        if args.command == 'feedback':
            if args.file:
                data = json.loads(args.file.read_text())
                if data.get('episode_sha256') != episode.manifest['sha256']:
                    parser.error('Feedback belongs to another episode')
                text, phase = data.get('text'), data.get('phase')
            else:
                text, phase = args.text, args.phase
            phases = {r['phase'] for r in episode.records() if r['kind'] == 'phase_start'} | {'overall'}
            if phase not in phases:
                parser.error('Feedback phase not in this episode')
            episode.append('feedback', phase=phase, source='user', details=dict(text=text))
        print(json.dumps(episode.summary(), indent=2))


if __name__ == '__main__':
    main()
