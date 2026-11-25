import os
import yaml
from pathlib import Path
from ament_index_python.packages import get_package_prefix, get_package_share_directory as share
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def start(context):
    # Subscribe to the running robot's URDF so measured camera extrinsics match.
    config = (MoveItConfigsBuilder('turtlebot3_manipulation', package_name='turtlebot3_manipulation_moveit_config')
              .robot_description(file_path=Path(share('turtlebot3_manipulation_description')) /
                                 'urdf/turtlebot3_manipulation.urdf.xacro')
              .planning_pipelines(pipelines=['ompl']).to_moveit_configs().to_dict())
    config.pop('robot_description', None)
    config['use_sim_time'] = LaunchConfiguration('use_sim_time')
    config['publish_robot_description_semantic'] = True
    if LaunchConfiguration('cumotion').perform(context).lower() == 'true':
        planner_yaml = Path(share('isaac_ros_cumotion_moveit'))/'config/isaac_ros_cumotion_planning.yaml'
        config['isaac_ros_cumotion'] = yaml.safe_load(planner_yaml.read_text())
        # Retiming yields a stopped terminal waypoint accepted by the standard trajectory controller.
        config['isaac_ros_cumotion']['response_adapters'] = [
            'default_planning_response_adapters/AddTimeOptimalParameterization',
            'default_planning_response_adapters/ValidateSolution']
        config['planning_pipelines'] = ['ompl', 'isaac_ros_cumotion']
    rviz = Path(share('turtlebot3_manipulation_moveit_config')) / 'config/moveit.rviz'
    # MoveIt 2.15.2 retains controller callbacks during shutdown. Keep their
    # plugin loaded until rclcpp has finished destroying the callback groups.
    plugin = Path(get_package_prefix('moveit_simple_controller_manager')) / 'lib/libmoveit_simple_controller_manager.so'
    preload = os.pathsep.join(filter(None, (str(plugin), os.environ.get('LD_PRELOAD'))))
    return [
        Node(package='moveit_ros_move_group', executable='move_group', parameters=[config],
             additional_env={'LD_PRELOAD': preload}),
        Node(package='rviz2', executable='rviz2', parameters=[config], arguments=['-d', str(rviz)],
             condition=IfCondition(LaunchConfiguration('rviz'))),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('cumotion', default_value='false'),
        OpaqueFunction(function=start),
    ])
