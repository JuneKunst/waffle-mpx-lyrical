"""Show task outcomes and closest approach for each instruction and layout."""
import argparse
import json
from math import dist
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('results', type=Path, help='Directory containing results.json and trial traces')
args = parser.parse_args()
report = json.loads((args.results / 'results.json').read_text())
print('layout   cube   picked   placed   lift_mm   min_tip_distance_mm')
for trial in report['results']:
    cube = trial['selected']
    directory = args.results / f"{trial['layout']:02d}-{cube}"
    with (directory / 'trace.jsonl').open() as stream:
        distance = min(dist(row['fingertips'], row['cubes'][cube]) for row in map(json.loads, stream))
    print(f"{trial['layout']:6} {cube:>6} {int(trial['picked']):8} {int(trial['success']):8}"
          f" {1000 * trial['max_lift_m'][cube]:9.3f} {1000 * distance:21.1f}")
print(f"Pick and place: {report['successes']}/{report['trials']} ({report['success_rate']:.1%})")
