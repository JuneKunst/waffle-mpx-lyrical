"""Reusable Isaac Lab 3.0 articulation for the robot USD exported by scene.py."""
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg
from isaaclab.sim import UsdFileCfg


def robot_config(usd_path, prim_path='/World/Robot'):
    return ArticulationCfg(
        prim_path=prim_path, spawn=UsdFileCfg(usd_path=str(usd_path)),
        init_state=ArticulationCfg.InitialStateCfg(pos=(0.,0.,0.015)),
        actuators={
            'base': ImplicitActuatorCfg(joint_names_expr=['wheel_.*_joint'],
                                        stiffness=0., damping=.06, joint_effort_limit=.6),
            'follower': ImplicitActuatorCfg(joint_names_expr=['gripper_right_joint'],
                                            stiffness=0., damping=0., joint_effort_limit=1.),
            'arm': ImplicitActuatorCfg(joint_names_expr=['joint[1-4]'],
                                       stiffness=20., damping=1., joint_effort_limit=1.),
            'gripper': ImplicitActuatorCfg(joint_names_expr=['gripper_left_joint'],
                                           stiffness=150., damping=5., joint_effort_limit=1.),
        })
