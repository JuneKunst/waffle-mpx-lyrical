from pathlib import Path
from ament_index_python.packages import get_package_share_directory as share
from nav2_common.launch import ReplaceString
from launch.conditions import IfCondition
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    params = ReplaceString(
        source_file=str(Path(share('turtlebot3_manipulation_bringup'))/'config/nav2.yaml'),
        replacements={'["voxel_layer", "inflation_layer"]': '["voxel_layer", "nvblox_layer", "inflation_layer"]'},
        condition=IfCondition(LaunchConfiguration('nvblox')))
    return LaunchDescription([
        DeclareLaunchArgument('nvblox', default_value='false'),
        DeclareLaunchArgument('map', description='Absolute path to the saved map YAML'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            str(Path(share('nav2_bringup')) / 'launch/bringup_launch.py')), launch_arguments={
                'map': LaunchConfiguration('map'), 'use_sim_time': LaunchConfiguration('use_sim_time'),
                'params_file': params,
                'use_keepout_zones': 'false', 'use_speed_zones': 'false',
            }.items()),
    ])
