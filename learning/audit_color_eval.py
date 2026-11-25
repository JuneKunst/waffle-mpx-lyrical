"""Verify the color checkpoint, unseen positions, and paired physical task results."""
import argparse
import hashlib
import json
from math import dist
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('checkpoint',type=Path)
parser.add_argument('evaluation',type=Path)
args = parser.parse_args()
manifest = json.loads(args.checkpoint.with_suffix('.json').read_text())
report = json.loads((args.evaluation/'results.json').read_text())
digest = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
if not (digest == manifest['checkpoint_sha256'] == report['checkpoint_sha256']):
    raise ValueError('Checkpoint and result fingerprints do not match')
if report['controller'] != 'color' or report['seed'] == manifest['seed']:
    raise ValueError('Expected an independent learned-policy run')
training = [xyz[:2] for demo in manifest['color_demos'] for xyz in demo['initial'].values()]
if any(not (.201 <= xy[0] <= .212 or .218 <= xy[0] <= .229) for xy in training):
    raise ValueError('A recorded training block lies outside its declared training bands')
rows = report['results']
if not rows or report['trials'] != len(rows) or report['successes'] != sum(r['success'] for r in rows):
    raise ValueError('Aggregate result disagrees with trial outcomes')
distances = []
for layout in sorted({row['layout'] for row in rows}):
    pair = [r for r in rows if r['layout'] == layout]
    if len(pair) != 2 or {r['selected'] for r in pair} != {'red','blue'}:
        raise ValueError(f'Missing paired instruction on layout {layout}')
    for color in ('red','blue'):
        if dist(pair[0]['initial'][color], pair[1]['initial'][color]) > .001:
            raise ValueError('Reset positions differ between instructions')
    for r in pair:
        color = r['selected']
        start = r['initial'][color][:2]
        nearest = min(dist(start,xy) for xy in training)
        distances.append(nearest)
        if not (.2129 <= start[0] <= .2171) or nearest < .001:
            raise ValueError('Evaluation position overlaps training or is outside the held-out band')
        if r['success'] and (r['wrong_pick'] or not r['picked'] or r['stable_s'] < .499):
            raise ValueError('Inconsistent physical outcome')
for color in ('red','blue'):
    subset = [r for r in rows if r['selected'] == color]
    print(f"{color}: picked {sum(r['picked'] for r in subset)}/{len(subset)}, placed {sum(r['success'] for r in subset)}/{len(subset)}")
print(f"Closest train/test XY positions: {1000*min(distances):.2f} mm")
print(f"Physical placement success: {sum(r['success'] for r in rows)}/{len(rows)}")
