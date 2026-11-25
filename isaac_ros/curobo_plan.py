"""Plan a Waffle joint-space trajectory offline with NVIDIA cuRobo 2."""
import argparse
from pathlib import Path
import json
import torch
from curobo.motion_planner import MotionPlanner, MotionPlannerCfg
from curobo.types import ContentPath, JointState
from curobo._src.robot.loader.util import load_robot_yaml

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('model',type=Path)
    p.add_argument('--start',type=float,nargs=4,default=[0.]*4)
    p.add_argument('--goal',type=float,nargs=4,default=[.18,-.1,.12,0.])
    p.add_argument('--scene',type=str,help='cuRobo world YAML in the robot base frame')
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    path=args.model.resolve()
    model=load_robot_yaml(ContentPath(robot_xrdf_absolute_path=str(path/'arm.xrdf'),
        robot_urdf_absolute_path=str(path/'arm.urdf'),robot_asset_absolute_path=str(path)))
    planner=MotionPlanner(MotionPlannerCfg.create(robot=model,scene_model=args.scene,num_ik_seeds=4,num_trajopt_seeds=4))
    def state(q):
        return JointState.from_position(torch.tensor([q],device='cuda',dtype=torch.float32),
                                        joint_names=[f'joint{i}' for i in range(1,5)])
    result=planner.plan_cspace(state(args.goal),state(args.start),max_attempts=3)
    if result is None or not result.success.any():
        raise SystemExit('cuRobo did not find a feasible trajectory')
    traj=result.get_interpolated_plan()
    q=traj.position.reshape(-1,4)
    n=len(q)
    print(f'cuRobo planned {n} joint samples',flush=True)
    if args.output:
        args.output.write_text(json.dumps(dict(joint_names=planner.joint_names,
            dt=float(traj.dt.flatten()[0]),positions=q[:n].cpu().tolist())))


if __name__ == '__main__':
    main()
