"""Plot measured Isaac joints alongside the commands sent by the learned policy."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('trace', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
rows = [json.loads(line) for line in args.trace.read_text().splitlines()]
applied = [row for row in rows if row['applied'] is not None]
if not applied:
    parser.error('Trace has no applied actions')
start = rows[0]['time']
fig, axes = plt.subplots(3, 2, figsize=(10, 8), constrained_layout=True)
for axis, index, name in zip(axes.flat, range(2, 7), ['Joint 1', 'Joint 2', 'Joint 3', 'Joint 4', 'Gripper']):
    scale = 1000 if index == 6 else 1
    axis.step([r['time'] - start for r in applied], [scale * r['applied'][index] for r in applied],
              where='post', color='#bd5d15', linestyle='--', label='Command')
    axis.plot([r['time'] - start for r in rows], [scale * r['state'][index] for r in rows],
              '.-', color='#145b76', label='Measured')
    axis.set(title=name, xlabel='Simulation time (s)', ylabel='mm' if index == 6 else 'rad')
    axis.grid(alpha=.2)
axes.flat[0].legend()
axes.flat[-1].axis('off')
fig.suptitle('Hugging Face policy in Isaac Sim 6.1')
fig.savefig(args.output, dpi=140)
