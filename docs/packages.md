# 패키지 목록

## 워크스페이스에서 빌드하는 ROS 패키지

패키지 이름은 각 디렉터리의 `package.xml` 기준이다. `vendor/`의 세 패키지는 [원본 리비전](../vendor/revisions.repos)과 함께 동봉했다.

| 패키지 | 역할 | 직접 선언한 빌드·실행 의존성 |
|---|---|---|
| [turtlebot3_manipulation_bringup](../turtlebot3_manipulation_bringup) | 실물·mock·Isaac 기동, 컨트롤러, 텔레옵, Nav2와 GPU launch | `ament_cmake`, `coin_d4_driver`, `geometry_msgs`, `nav2_bringup`, `nav2_common`, `rclpy`, `realsense2_camera`, `robot_state_publisher`, `ros2_control`, `ros2_controllers`, `rviz2`, `sensor_msgs`, `topic_based_ros2_control`, `trajectory_msgs`, `turtlebot3_manipulation_description`, `turtlebot3_manipulation_hardware`, `xacro` |
| [turtlebot3_manipulation_cartographer](../turtlebot3_manipulation_cartographer) | Cartographer ROS 온라인 노드와 LDS-03 매핑 설정 | `ament_cmake`, `cartographer_ros`, `cartographer_ros_msgs`, `eigen`, `libabsl-dev`, `libgoogle-glog-dev`, `nav_msgs`, `rclcpp`, `rviz2`, `sensor_msgs`, `tf2_ros`, `urdf`, `visualization_msgs` |
| [turtlebot3_manipulation_description](../turtlebot3_manipulation_description) | Waffle, 팔, LDS, D435, 마운트의 URDF·메시·TF | `ament_cmake`, `joint_state_publisher`, `joint_state_publisher_gui`, `robot_state_publisher`, `rviz2`, `xacro` |
| [turtlebot3_manipulation_hardware](../turtlebot3_manipulation_hardware) | OpenCR과 바퀴·팔·그리퍼를 연결하는 ros2_control 하드웨어 플러그인 | `ament_cmake`, `dynamixel_sdk`, `hardware_interface`, `pluginlib`, `rclcpp` |
| [turtlebot3_manipulation_moveit_config](../turtlebot3_manipulation_moveit_config) | 팔·그리퍼 계획 그룹, OMPL·cuMotion 설정과 RViz | `ament_cmake`, `joint_state_publisher`, `joint_state_publisher_gui`, `moveit_configs_utils`, `moveit_kinematics`, `moveit_planners`, `moveit_ros_move_group`, `moveit_ros_visualization`, `moveit_ros_warehouse`, `moveit_simple_controller_manager`, `robot_state_publisher`, `rviz2`, `rviz_common`, `rviz_default_plugins`, `srdfdom`, `tf2_ros`, `turtlebot3_manipulation_description`, `xacro` |
| [coin_d4_driver](../vendor/coin_d4_driver) | USB2LDS로 연결된 LDS-03 스캔 수신 | `ament_cmake`, `geometry_msgs`, `rclcpp`, `rclcpp_lifecycle`, `sensor_msgs` |
| [dynamixel_sdk](../vendor/dynamixel_sdk) | OpenCR 통신에 사용하는 DYNAMIXEL SDK | `ament_cmake`, `ament_cmake_python` |
| [topic_based_ros2_control](../vendor/topic_based_ros2_control) | 관절 명령·피드백 토픽으로 Isaac과 ros2_control 연결 | `ament_cmake`, `angles`, `hardware_interface`, `rclcpp`, `sensor_msgs` |

## NVIDIA GPU 호스트용 선택 패키지

다음 표는 [설치 스크립트가 사용하는 목록](../isaac_ros/packages.txt)이다. 각 이름 앞에 `ros-lyrical-`을 붙이면 APT 패키지명이 된다. 설치한 launch 파일·컴포넌트는 `source tools/isaac_env.bash` 후 `python3 isaac_ros/catalog.py`로 조회한다. 모델과 센서 입력은 [GPU 실습 안내](../isaac_ros/README.md)를 따른다.

| 패키지 | 패키지 | 패키지 |
|---|---|---|
| `isaac-ros-apriltag` | `isaac-ros-cumotion` | `isaac-ros-cumotion-moveit` |
| `isaac-ros-cumotion-object-attachment` | `isaac-ros-cumotion-robot-segmenter` | `isaac-ros-cuvslam` |
| `isaac-ros-nvblox` | `isaac-ros-image-pipeline` | `isaac-ros-depth-image-proc` |
| `isaac-ros-stereo-image-proc` | `isaac-ros-ess` | `isaac-ros-foundationstereo` |
| `isaac-ros-foundationpose` | `isaac-ros-detectnet` | `isaac-ros-rtdetr` |
| `isaac-ros-yolov8` | `isaac-ros-grounding-dino` | `isaac-ros-dope` |
| `isaac-ros-centerpose` | `isaac-ros-unet` | `isaac-ros-segformer` |
| `isaac-ros-segment-anything` | `isaac-ros-segment-anything2` | `isaac-ros-visual-mapping` |
| `isaac-ros-visual-global-localization` | `isaac-ros-occupancy-grid-localizer` | `isaac-ros-pointcloud-utils` |
| `isaac-ros-pose-proc` | `isaac-ros-h264-encoder` | `isaac-ros-h264-decoder` |
| `isaac-ros-tensor-rt` | `isaac-ros-triton` | `isaac-ros-tensor-proc` |
| `isaac-ros-tensor-inspector` | `isaac-ros-dnn-image-encoder` | `isaac-ros-deploy` |
| `isaac-ros-scene-recorder` | `isaac-ros-data-flywheel` | `isaac-ros-teleop` |
| `isaac-ros-benchmark` | `isaac-ros-examples` | `isaac-ros-launch-utils` |

## Python과 설계 도구

| 환경 | 사용 패키지와 용도 |
|---|---|
| Isaac Sim 6.1 | PhysX 물리, USD 로봇 가져오기, Replicator RGB·깊이 렌더링. ROS 브리지에는 Lyrical의 `rclpy`, `sensor_msgs`, `rosgraph_msgs`가 필요하다. |
| Isaac Lab 3 | Newton·MJWarp 물리 환경, CUDA PyTorch, Stable-Baselines3 PPO |
| VLA·모방학습 | Transformers·Hugging Face Hub로 모델과 시연을 읽고, PyArrow·PyAV로 프레임을 맞춘다. NumPy·Pillow는 전처리, Matplotlib은 평가 결과 시각화에 사용한다. [설치 버전](../learning/requirements.txt) |
| 계획·추론 | cuRobo 2의 Python API는 독립 관절 계획 예제에서 사용한다. TensorRT와 `trtexec`는 YOLO 엔진 생성에 사용한다. |
| 마운트 | Bambu Studio에서 제공된 3MF를 열 수 있다. 형상을 재생성하는 Python 스크립트는 NumPy와 manifold3d를 사용한다. |
