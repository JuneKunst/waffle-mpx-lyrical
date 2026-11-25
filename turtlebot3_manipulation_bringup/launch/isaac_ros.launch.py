from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('input_qos', default_value='DEFAULT'),
        ComposableNodeContainer(
            name='camera_processing', namespace='', package='rclcpp_components',
            executable='component_container', composable_node_descriptions=[
                ComposableNode(package='isaac_ros_image_proc', plugin='nvidia::isaac_ros::image_proc::ImageFormatConverterNode',
                               name='color_converter', namespace='camera/color',
                               remappings=[('image','image_mono')],
                               parameters=[{'encoding_desired': 'mono8','image_width': 640,'image_height': 480,
                                            'input_qos': LaunchConfiguration('input_qos'),
                                            'use_sim_time': LaunchConfiguration('use_sim_time')}])
            ]),
    ])
