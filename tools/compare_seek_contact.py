#!/usr/bin/env python3
"""Compare two regular Gazebo episodes of the same contact-search recipe."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def read(path):
    return json.loads(path.read_text())


def compare(nominal, raised, output):
    output.mkdir(parents=True, exist_ok=True)
    cases = []
    figure, axes = plt.subplots(1, 2, figsize=(10, 4), sharex=True)
    for directory, color, name in [(nominal, '#155b96', 'Nominelle Wand'),
                                   (raised, '#aa4b12', 'Wand +2 mm')]:
        result = read(directory/'seek-result.json')
        trace = read(directory/'seek-force-trace.json')
        state = read(directory/'state.json')
        if not trace:
            raise ValueError(f'Keine Kraft-Weg-Messwerte in {directory}')
        rows = [r for r in trace if r['phase'] in ('search', 'cancel')]
        distance = [r['travel_m']*1000 for r in rows]
        axes[0].plot(distance,[r['force_n'] for r in rows],label=name,color=color)
        axes[1].plot(distance,[r['pair_mean_n'] for r in rows],label=name,color=color)
        if 'hit' in result:
            axes[0].plot(result['hit']['travel_m']*1000,result['hit_force_n'],'o',color=color)
        cases.append(dict(directory=str(directory.resolve()),run_state=state['state'],result=result))
    first, second = (case['result'] for case in cases)
    if first['recipe'] != second['recipe']:
        raise ValueError('Die Versuche verwenden unterschiedliche Rezepte')
    axes[0].axhline(first['recipe']['threshold_n'],ls=':',color='#404040',label='Auslöseschwelle')
    for axis, title in zip(axes,['Handgelenk, tariert','Kontaktpaar Spitze–Wand']):
        axis.set(title=title,xlabel='Weg ab Vorposition [mm]',ylabel='Normalkraft [N], Mittel über 10 ms')
        axis.grid(alpha=.22)
        axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output/'kraft-weg.png',dpi=155)
    plt.close(figure)
    comparison = dict(cases=cases,expected_difference_mm=2.0)
    if all('hit' in item for item in (first,second)):
        difference = 1000*(first['hit']['travel_m']-second['hit']['travel_m'])
        comparison.update(measured_difference_mm=difference,deviation_mm=difference-2.)
    (output/'comparison.json').write_text(json.dumps(comparison,indent=2,allow_nan=False)+'\n')
    return comparison


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('nominal','raised','output'):
        parser.add_argument(arg,type=Path)
    args = parser.parse_args()
    result = compare(args.nominal,args.raised,args.output)
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
