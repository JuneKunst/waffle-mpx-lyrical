"""Run an installed NVIDIA graph or graph fragments with Waffle D435 inputs."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory as share
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import SetParameter, Node


def build(context):
    def arg(name):return LaunchConfiguration(name).perform(context)
    fragments=arg('fragments')
    if fragments:
        source=Path(share('isaac_ros_examples'))/'launch/isaac_ros_examples.launch.py'
        inputs={'launch_fragments':fragments,'interface_specs_file':arg('specs')}
    else:
        if not arg('package') or not arg('file'): raise ValueError('Specify fragments or package and file')
        source=Path(share(arg('package')))/'launch'/arg('file')
        inputs={}
    # Several bundled DNN graphs hardcode absolute input names on their components.
    # Publish compatible inputs even when an inner launch remaps its own subscriptions.
    actions=[]
    if arg('streams'):
        actions.append(Node(package='turtlebot3_manipulation_bringup',executable='gpu_inputs',
                            parameters=[{'streams':arg('streams')}]))
    return [GroupAction([SetParameter('use_sim_time',arg('use_sim_time').lower()=='true'),*actions,
        IncludeLaunchDescription(AnyLaunchDescriptionSource(str(source)),launch_arguments=inputs.items())])]


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('package',default_value=''),
        DeclareLaunchArgument('file',default_value=''),DeclareLaunchArgument('streams',default_value='rgb'),DeclareLaunchArgument('fragments',default_value=''),
        DeclareLaunchArgument('use_sim_time',default_value='false'),
        DeclareLaunchArgument('specs',default_value=str(Path(share('turtlebot3_manipulation_bringup'))/'config/d435_interface.json')),
        OpaqueFunction(function=build)])
