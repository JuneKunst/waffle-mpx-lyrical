"""Start the Waffle MPX controllers and the hardware for the selected backend."""
from pathlib import Path

import xacro
from ament_index_python.packages import get_package_share_directory as share
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def start(context):
    def arg(name):
        return LaunchConfiguration(name).perform(context)

    mode = arg('mode')
    simulated = mode == 'isaac'
    description = Path(share('turtlebot3_manipulation_description'))
    model = xacro.process_file(str(description / 'urdf/turtlebot3_manipulation.urdf.xacro'), mappings={
        'use_sim': str(simulated).lower(),
        'use_fake_hardware': str(mode == 'mock').lower(),
        'opencr_port': arg('opencr_port'),
        'camera_mount_xyz': arg('camera_mount_xyz'),
        'camera_mount_rpy': arg('camera_mount_rpy'),
    }).toxml()
    clock = {'use_sim_time': simulated}
    config = str(Path(share('turtlebot3_manipulation_bringup')) / 'config/hardware_controller_manager.yaml')
    controllers = ['joint_state_broadcaster', 'diff_drive_controller', 'arm_controller', 'gripper_controller']
    nodes = [
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[clock, {'robot_description': ParameterValue(model, value_type=str)}]),
        Node(package='controller_manager', executable='ros2_control_node', parameters=[clock, config]),
    ]
    if mode == 'hardware':
        controllers.append('imu_broadcaster')
        nodes.extend([
            Node(package='coin_d4_driver', executable='single_coin_d4_node',
                 parameters=[str(Path(share('coin_d4_driver')) / 'params/single_lidar_node.yaml'),
                             {'port': arg('lidar_port'), 'frame_id': 'base_scan'}]),
            IncludeLaunchDescription(PythonLaunchDescriptionSource(
                str(Path(share('realsense2_camera')) / 'launch/rs_launch.py')), launch_arguments={
                    'camera_namespace': '', 'camera_name': 'camera', 'align_depth.enable': 'true', 'enable_sync': 'true',
                    'config_file': str(Path(share('turtlebot3_manipulation_bringup'))/'config/d435_stereo.yaml') if arg('stereo').lower()=='true' else "''",
                    'enable_infra1': arg('stereo'), 'enable_infra2': arg('stereo'),
                    'depth_module.infra_profile': '640,480,30',
                    'depth_module.depth_profile': '640,480,30', 'rgb_camera.color_profile': '640,480,30',
                }.items()),
        ])
    nodes.append(Node(package='controller_manager', executable='spawner',
                      arguments=[*controllers, '--param-file', config, '--activate-as-group', '--switch-timeout', '120',
                                 '--controller-ros-args',
                                 '-r /diff_drive_controller/cmd_vel:=/cmd_vel -r /diff_drive_controller/odom:=/odom -r /imu_broadcaster/imu:=/imu']))
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('mode', default_value='hardware', choices=['hardware', 'mock', 'isaac']),
        DeclareLaunchArgument('stereo', default_value='false'),
        DeclareLaunchArgument('opencr_port', default_value='/dev/ttyACM0'),
        DeclareLaunchArgument('lidar_port', default_value='/dev/ttyUSB0'),
        DeclareLaunchArgument('camera_mount_xyz', default_value='0.1061547 0 0.065'),
        DeclareLaunchArgument('camera_mount_rpy', default_value='0 0 0'),
        OpaqueFunction(function=start),
    ])
