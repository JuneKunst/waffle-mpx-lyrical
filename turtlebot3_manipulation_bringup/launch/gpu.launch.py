"""Compose Waffle camera processing or start the Waffle cuMotion action servers."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory as share
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode

PROFILES=['vslam_rgbd','vslam_stereo','resize','rectify','crop','flip','apriltag',
          'pointcloud','nvblox','cumotion','h264','xyzrgb']


def start(context):
    def arg(name):return LaunchConfiguration(name).perform(context)
    selected=arg('profile')
    if selected=='cumotion':
        model=Path(arg('model_dir')).expanduser().resolve()
        for name in ('arm.urdf','arm.xrdf'):
            if not (model/name).is_file():raise FileNotFoundError(f'{model/name}: run isaac_ros/prepare_planner.py')
        launch=Path(share('isaac_ros_cumotion'))/'launch/isaac_ros_cumotion.launch.py'
        return [IncludeLaunchDescription(PythonLaunchDescriptionSource(str(launch)),launch_arguments={
            'cumotion_action_server.urdf_file_path':str(model/'arm.urdf'),
            'cumotion_action_server.xrdf_file_path':str(model/'arm.xrdf'),
            'cumotion_action_server.read_esdf_world':arg('use_esdf')}.items())]
    color='/camera/color/'
    depth='/camera/aligned_depth_to_color/'
    params={'use_sim_time':arg('use_sim_time').lower()=='true'}
    remaps=[]
    if selected.startswith('vslam'):
        package='isaac_ros_cuvslam'
        plugin='nvidia::isaac_ros::visual_slam::VisualSlamNode'
        stereo=selected=='vslam_stereo'
        frames=['infra1','infra2'] if stereo else ['color']
        params.update(tracking_mode=0 if stereo else 2,rectified_images=stereo,num_cameras=len(frames),
            min_num_images=len(frames),camera_optical_frames=[f'camera_{v}_optical_frame' for v in frames],
            depth_scale_factor=1000.,base_frame='base_link',enable_localization_n_mapping=True,
            publish_map_to_odom_tf=False,publish_odom_to_base_tf=False,image_jitter_threshold_ms=100.)
        for i,stream in enumerate(frames):
            remaps.extend([(f'visual_slam/image_{i}',f'/camera/{stream}/'+('image_rect_raw' if stereo else 'image_raw')),
                           (f'visual_slam/camera_info_{i}',f'/camera/{stream}/camera_info')])
        if not stereo: remaps.append(('visual_slam/depth_0',depth+'image_raw'))
    elif selected=='nvblox':
        package='nvblox_ros';plugin='nvblox::NvbloxNode'
        params.update(global_frame='odom',voxel_size=.04,num_cameras=1,use_lidar=False,
                      input_qos=arg('input_qos'),esdf_mode=arg('esdf_mode'),
                      map_clearing_frame_id='base_link',esdf_slice_bounds_visualization_attachment_frame_id='base_link',
                      **{'static_mapper.esdf_slice_min_height':.035,'static_mapper.esdf_slice_max_height':.40,
                         'static_mapper.esdf_slice_height':.08})
        remaps=[('camera_0/depth/image',depth+'image_raw'),('camera_0/depth/camera_info',depth+'camera_info'),
                ('camera_0/color/image',color+'image_raw'),('camera_0/color/camera_info',color+'camera_info')]
    elif selected=='h264':
        backend=arg('h264_backend')
        if backend=='nvenc' or (backend=='auto' and Path('/usr/lib/x86_64-linux-gnu').is_dir() and
                                not Path('/usr/lib/x86_64-linux-gnu/libv4l/plugins/libcuvidv4l2_plugin.so').exists()):
            return [Node(package='turtlebot3_manipulation_bringup',executable='gpu_h264',parameters=[params, {'input_qos':arg('input_qos')}])]
        package='isaac_ros_h264_encoder';plugin='nvidia::isaac_ros::h264_encoder::EncoderNode'
        params.update(input_width=640,input_height=480)
        remaps=[('image_raw',color+'image_raw'),('image_compressed','/waffle/h264')]
    elif selected=='xyzrgb':
        package='isaac_ros_depth_image_proc';plugin='nvidia::isaac_ros::depth_image_proc::PointCloudXyzrgbNode'
        params.update(input_qos=arg('input_qos'))
        remaps=[('rgb/image_rect_color',color+'image_raw'),('rgb/camera_info',depth+'camera_info'),
                ('depth_registered/image_rect',depth+'image_raw'),('points','/waffle/points_rgb')]
    elif selected=='pointcloud':
        params.update(input_qos=arg('input_qos'))
        package='isaac_ros_depth_image_proc';plugin='nvidia::isaac_ros::depth_image_proc::PointCloudXyzNode'
        remaps=[('image_rect',depth+'image_raw'),('camera_info',depth+'camera_info'),('points','/waffle/points')]
    elif selected=='apriltag':
        package='isaac_ros_apriltag';plugin='nvidia::isaac_ros::apriltag::AprilTagNode'
        params.update(size=float(arg('tag_size')),tag_family='tag36h11')
        remaps=[('image',color+'image_raw'),('camera_info',color+'camera_info')]
    else:
        package='isaac_ros_image_proc'
        name={'crop':'Crop','flip':'ImageFlip','resize':'Resize','rectify':'Rectify'}[selected]
        plugin=f'nvidia::isaac_ros::image_proc::{name}Node'
        params.update(input_qos=arg('input_qos'))
        if selected in ('rectify','resize'):params.update(output_width=640 if selected=='rectify' else 320,output_height=480 if selected=='rectify' else 240)
        if selected=='crop':params.update(input_width=640,input_height=480,crop_width=320,crop_height=240,crop_mode='CENTER')
        remaps=[('image',color+'image_raw'),('image_raw',color+'image_raw'),('camera_info',color+'camera_info')]
    preprocessing=[]
    if selected in ('pointcloud','xyzrgb'):
        metric='/waffle/'+selected+'/depth_m'
        preprocessing.append(ComposableNode(package=package,
            plugin='nvidia::isaac_ros::depth_image_proc::ConvertMetricNode',name=selected+'_convert_metric',
            parameters=[{'input_qos':arg('input_qos'),'use_sim_time':params['use_sim_time']}],
            remappings=[('image_raw',depth+'image_raw'),('image',metric)]))
        remaps=[(src,metric if dst==depth+'image_raw' else dst) for src,dst in remaps]
    share(package)
    node=ComposableNode(package=package,plugin=plugin,name='nvblox_node' if selected=='nvblox' else 'waffle_'+selected,
                        parameters=[params],remappings=remaps)
    return [ComposableNodeContainer(name='gpu_'+selected,namespace='',package='rclcpp_components',
                executable='component_container_mt',composable_node_descriptions=preprocessing+[node],output='screen')]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('profile',choices=PROFILES),
        DeclareLaunchArgument('use_sim_time',default_value='false'),
        DeclareLaunchArgument('h264_backend',default_value='auto',choices=['auto','isaac','nvenc']),
        DeclareLaunchArgument('input_qos',default_value='SENSOR_DATA'),
        DeclareLaunchArgument('tag_size',default_value='0.16'),
        DeclareLaunchArgument('esdf_mode',default_value='2d',choices=['2d','3d']),
        DeclareLaunchArgument('use_esdf',default_value='false'),
        DeclareLaunchArgument('model_dir',default_value=str(Path.home()/'waffle_mpx/simulation/planner')),
        OpaqueFunction(function=start)])
