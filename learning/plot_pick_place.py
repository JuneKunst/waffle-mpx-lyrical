"""Plot paired D435 observations and measured color-block motion for one layout."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run',type=Path)
parser.add_argument('output',type=Path)
parser.add_argument('--layout',type=int,default=0)
args = parser.parse_args()
fig, axes = plt.subplots(2,4,figsize=(13,5.8),constrained_layout=True,
                         gridspec_kw={'width_ratios':[1.1,1.1,1.,1.]})
palette = {'red':'#c84037', 'blue':'#2868b4'}
for row, selected in enumerate(('red','blue')):
    trial = args.run / f'{args.layout:02d}-{selected}'
    result = json.loads((trial/'result.json').read_text())
    frames = [json.loads(line) for line in (trial/'trace.jsonl').read_text().splitlines()]
    time = np.arange(len(frames))*.25+.25
    for ax, filename, title in zip(axes[row,:2], ('start.png','end.png'),('Start RGB','Final RGB')):
        with Image.open(trial/filename) as image:
            ax.imshow(image)
        ax.set_axis_off()
        ax.set_title(f'{selected.capitalize()} instruction · {title}')
    xy, height = axes[row,2:]
    goal = np.array(result['goal'])*1000
    xy.add_patch(plt.Rectangle(goal-26,52,52,fc='#a7d2a3',ec='#397737',alpha=.6))
    for color, ink in palette.items():
        positions = 1000*np.array([frame['cubes'][color] for frame in frames])
        initial = np.array(result['initial'][color])*1000
        xy.plot(positions[:,0],positions[:,1],color=ink)
        xy.scatter(*initial[:2],marker='o',facecolors='white',edgecolors=ink)
        xy.scatter(*positions[-1,:2],marker='x',color=ink)
        height.plot(time,positions[:,2]-initial[2],color=ink,label=color)
    xy.set(xlim=(190,285),ylim=(-40,60),aspect='equal',xlabel='World x (mm)',ylabel='y (mm)',
           title='Start ○   End ×')
    height.axhline(25,color='.5',ls='--',lw=1)
    height.set(xlabel='Simulation time (s)',ylabel='Rise from start (mm)',ylim=(-5,85),
               title=f"Placement: {'success' if result['success'] else 'failure'}")
    height.legend(loc='upper right',fontsize=8)
fig.savefig(args.output,dpi=140)
