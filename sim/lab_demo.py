"""Roll out a short differential-drive and arm command in Isaac Lab 3.0."""
import argparse
from pathlib import Path
from isaaclab.app import add_launcher_args, launch_simulation

parser = argparse.ArgumentParser()
parser.add_argument('usd', type=Path)
parser.add_argument('--physics', choices=['newton_mjwarp','physx'],default='newton_mjwarp')
parser.add_argument('--steps', type=int, default=240)
add_launcher_args(parser)
args = parser.parse_args()

import torch
import isaaclab.sim as sim_utils
from isaaclab.assets import AssetBaseCfg
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
from isaaclab.utils import configclass
from lab_robot import robot_config

if args.physics == 'newton_mjwarp':
    from isaaclab_newton.physics import NewtonCfg
    cfg = sim_utils.SimulationCfg(dt=1/240, device=args.device,physics=NewtonCfg())
else:
    cfg = sim_utils.SimulationCfg(dt=1/240, device=args.device)
with launch_simulation(cfg,args):
    sim = sim_utils.SimulationContext(cfg)
    @configclass
    class WaffleScene(InteractiveSceneCfg):
        ground = AssetBaseCfg(prim_path='/World/Ground', spawn=sim_utils.GroundPlaneCfg())
        waffle = robot_config(args.usd.resolve(), '{ENV_REGEX_NS}/Robot')

    scene = InteractiveScene(WaffleScene(num_envs=1,env_spacing=3.))
    robot = scene['waffle']
    sim.reset()
    wheel_ids,_ = robot.find_joints('wheel_.*_joint')
    joint_ids,_ = robot.find_joints('joint1')
    for i in range(args.steps):
        speed = 2. if i < args.steps//2 else 0.
        cmd = robot.actuators.target_command
        cmd.set_velocity_index(value=torch.full((1,2),speed,device=sim.device), joint_ids=wheel_ids)
        cmd.set_position_index(value=torch.full((1,1),.25,device=sim.device), joint_ids=joint_ids)
        robot.write_data_to_sim()
        sim.step()
        robot.update(sim.get_physics_dt())
    print('Final joint positions',dict(zip(robot.joint_names,robot.data.joint_pos.torch[0].cpu().tolist())))
