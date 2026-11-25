"""Run the frozen policy in its training environment over a local pipe."""
import json
import sys
from PIL import Image
from policy import Policy

if len(sys.argv) == 3:
    from pathlib import Path
    from color_imitation import ColorPolicy
    policy = ColorPolicy(Path(sys.argv[1]), Path(sys.argv[2]))
else:
    policy = Policy(sys.argv[1], 'cuda')
print(json.dumps({'ready': True}), flush=True)
for line in sys.stdin:
    obs = json.loads(line)
    with Image.open(obs['rgb']) as frame:
        predict = policy.plan if len(sys.argv) == 3 else policy.predict
        action = predict(frame, obs['instruction'], obs['state'])
    print(json.dumps(action.tolist(), allow_nan=False), flush=True)
