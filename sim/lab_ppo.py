"""Train or evaluate PPO on a Waffle arm posture task in Isaac Lab 3 Newton."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'learning'))
from actions import JOINTS, normalized, physical
from isaaclab.app import add_launcher_args, launch_simulation

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('usd', type=Path)
parser.add_argument('checkpoint', type=Path)
parser.add_argument('--timesteps', type=int, default=16384)
parser.add_argument('--rollout', type=int, default=128)
parser.add_argument('--eval-episodes', type=int, default=0)
parser.add_argument('--resume', action='store_true')
parser.add_argument('--task',choices=['shoulder','posture'],default='shoulder')
parser.add_argument('--seed', type=int, default=42)
add_launcher_args(parser)
args = parser.parse_args()
import gymnasium as gym
import numpy as np
import torch
from stable_baselines3 import PPO
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
from isaaclab.sim import SimulationCfg, SimulationContext, GroundPlaneCfg
from isaaclab.assets import AssetBaseCfg
from isaaclab.utils import configclass
from isaaclab_newton.physics import NewtonCfg
from lab_robot import robot_config


@configclass
class Scene(InteractiveSceneCfg):
    ground = AssetBaseCfg(prim_path='/World/Ground', spawn=GroundPlaneCfg())
    robot = robot_config(args.usd.resolve(), '{ENV_REGEX_NS}/Robot')


class Posture(gym.Env):
    """Learn residual corrections to position targets for a stationary-base reaching task."""
    action_space = gym.spaces.Box(-1., 1., (5,), np.float32)
    observation_space = gym.spaces.Box(-1., 1., (10,), np.float32)

    def __init__(self, sim, scene):
        self.sim, self.scene, self.robot = sim, scene, scene['robot']
        self.ids = [self.robot.find_joints(name)[0][0] for name in JOINTS]

    def observe(self):
        q = self.robot.data.joint_pos.torch[0,self.ids].cpu().numpy()
        return np.concatenate([normalized(np.r_[0.,0.,q])[2:], self.goal]).astype(np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        r = self.robot
        r.write_root_pose_to_sim_index(root_pose=r.data.default_root_pose.torch.clone())
        r.write_root_velocity_to_sim_index(root_velocity=r.data.default_root_vel.torch.clone())
        r.write_joint_position_to_sim_index(position=r.data.default_joint_pos.torch.clone())
        r.write_joint_velocity_to_sim_index(velocity=r.data.default_joint_vel.torch.clone())
        self.scene.reset()
        r.actuators.target_command.set_position_index(value=r.data.default_joint_pos.torch[:,self.ids], joint_ids=self.ids)
        self.scene.write_data_to_sim()
        self.sim.step()
        self.scene.update(self.sim.get_physics_dt())
        target = self.np_random.uniform([-.55,-.35,-.1,-.4,0.], [.55,.35,.6,.4,.014])
        self.goal = normalized(np.r_[0.,0.,target])[2:]
        self.steps = self.held = 0
        return self.observe(), {}

    def step(self, action):
        corrected = np.clip(self.goal + .30*action, -1., 1.)
        target = physical(np.r_[0.,0.,corrected])[2:]
        cmd = torch.tensor(target, device=self.robot.device, dtype=torch.float32)[None,:]
        self.robot.actuators.target_command.set_position_index(value=cmd, joint_ids=self.ids)
        for _ in range(12):
            self.scene.write_data_to_sim()
            self.sim.step()
            self.scene.update(self.sim.get_physics_dt())
        obs = self.observe()
        error = np.abs(obs[:5]-obs[5:])
        self.held = self.held+1 if error.max()<.08 else 0
        self.steps += 1
        success = self.held >= 5
        return obs, float(-error.mean()-error.max()+success), success, self.steps>=80, {'is_success':success}


class Shoulder(Posture):
    """Train a direct position policy for joint1 with a changing yaw target."""
    action_space = gym.spaces.Box(-1., 1., (1,), np.float32)
    observation_space = gym.spaces.Box(-1., 1., (2,), np.float32)

    def shoulder_observation(self):
        q=float(self.robot.data.joint_pos.torch[0,self.ids[0]].item())
        return np.clip([q/.7,self.shoulder_goal/.7],-1.,1.).astype(np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed,options=options)
        self.shoulder_goal=self.np_random.uniform(-.55,.55)
        return self.shoulder_observation(),{}

    def step(self, action):
        target=torch.tensor([[.7*float(action[0]),0.,0.,0.,.003]],device=self.robot.device)
        self.robot.actuators.target_command.set_position_index(value=target,joint_ids=self.ids)
        for _ in range(12):
            self.scene.write_data_to_sim()
            self.sim.step()
            self.scene.update(self.sim.get_physics_dt())
        obs=self.shoulder_observation()
        error=abs(float(self.robot.data.joint_pos.torch[0,self.ids[0]].item())-self.shoulder_goal)
        self.held=self.held+1 if error<.07 else 0
        self.steps+=1
        success=self.held>=5
        return obs,float(-error+success),success,self.steps>=80,{'is_success':success}


torch.set_num_threads(1)
config = SimulationCfg(dt=1/240,device=args.device,physics=NewtonCfg())
with launch_simulation(config,args):
    sim = SimulationContext(config)
    scene = InteractiveScene(Scene(num_envs=1,env_spacing=3.))
    sim.reset()
    env = (Shoulder if args.task=='shoulder' else Posture)(sim,scene)
    if args.eval_episodes or args.resume:
        policy = PPO.load(args.checkpoint, env=env, device='cpu')
    else:
        policy = PPO('MlpPolicy',env,device='cpu',seed=args.seed,n_steps=args.rollout,
                     batch_size=min(64,args.rollout),verbose=1)
    if args.eval_episodes:
        wins = 0
        for i in range(args.eval_episodes):
            obs,_ = env.reset(seed=args.seed+i)
            while True:
                obs,_,done,truncated,info = env.step(policy.predict(obs,deterministic=True)[0])
                if done or truncated:
                    wins += info['is_success']
                    print('Final normalized joint errors',np.abs(obs[:len(obs)//2]-obs[len(obs)//2:]).round(3).tolist())
                    break
        print(f'Goal held in {wins}/{args.eval_episodes} episodes')
    else:
        policy.learn(args.timesteps,reset_num_timesteps=not args.resume)
        args.checkpoint.parent.mkdir(parents=True,exist_ok=True)
        policy.save(args.checkpoint)
