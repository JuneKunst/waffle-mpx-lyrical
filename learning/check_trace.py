"""Check command-direction agreement and measured shoulder motion in the Isaac example."""
import argparse
import json
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace',type=Path)
args=p.parse_args()
rows=[json.loads(l) for l in args.trace.read_text().splitlines()]
if len(rows)<3:raise ValueError('Too few observations')
states=np.array([r['state'] for r in rows])
applied=[r for r in rows if r['applied'] is not None]
if not applied:raise RuntimeError('All observations were too stale for a command')
commands=np.array([r['applied'] for r in applied])
# Compare shaft rotation to the command before the next camera frame.
pairs=[(r['applied'][2]-r['state'][2],s['state'][2]-r['state'][2]) for r,s in zip(rows,rows[1:])
       if r['applied'] is not None and abs(r['applied'][2]-r['state'][2])>.01]
agreement=float(np.mean([a*b>0 for a,b in pairs])) if pairs else 0.
span=np.ptp(states[:,2:],axis=0)
report=dict(frames=len(rows),applied=len(applied),joint_span=span.tolist(),
            max_abs_base_command=np.abs(commands[:,:2]).max(0).tolist(),
            joint1_direction_agreement=agreement,directional_samples=len(pairs))
print(json.dumps(report,indent=2))
# The base must stay parked and shoulder motion must follow the predicted directions.
ok=span[0]>.025 and len(pairs)>=3 and agreement>.6 and np.abs(commands[:,:2]).max()<1e-5
if not ok:raise SystemExit('Joint motion verification did not pass')
