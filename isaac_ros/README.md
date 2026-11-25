# Waffle에서 Isaac ROS 실행하기

GPU 작업은 NVIDIA 호스트에서 실행합니다. Raspberry Pi는 LDS-03, D435, OpenCR와 관절 제어를 담당합니다. 시뮬레이터와 GPU 노드는 같은 ROS 도메인과 시간을 사용합니다. 실물과 연결할 때는 Pi와 도메인을 맞추고 시뮬레이션 시간을 끕니다.

```bash
cd ~/waffle_mpx/src
source tools/isaac_env.bash
export ROS_DOMAIN_ID=43
python3 isaac_ros/catalog.py
```

현재 PC에서는 워크스페이스의 Isaac ROS 5 오버레이를 사용합니다. 다른 GPU 호스트에서는 Lyrical용 NVIDIA 패키지 저장소를 구성한 후 `isaac_ros/install_gpu.bash --preview`로 의존성을 확인하고 `isaac_ros/install_gpu.bash`로 설치합니다. MoveIt 플러그인과 로컬 MoveIt의 ABI가 다르면 `isaac_ros/build_moveit_plugin.sh`로 이 환경에 맞춰 빌드한 뒤 환경을 다시 불러옵니다. [NVIDIA 패키지 목록](https://nvidia-isaac-ros.github.io/v/release-5.0/repositories_and_packages/index.html)

## D435 영상과 지도

시뮬레이션을 시작한 뒤 같은 도메인의 별도 터미널에서 원하는 프로필을 실행합니다. IR 스테레오 실험에는 시뮬레이터의 `sim/scene.py --stereo` 옵션 또는 실제 로봇의 `robot.launch.py stereo:=true`가 필요합니다. 실물 스테레오 설정은 IR 패턴이 특징 추적을 방해하지 않도록 프로젝터를 끄므로 저텍스처 표면에서 깊이 품질이 달라질 수 있습니다.

```bash
ros2 launch turtlebot3_manipulation_bringup gpu.launch.py profile:=vslam_stereo use_sim_time:=true
```

| 프로필 | 검증 결과 또는 관측 지점 |
|---|---|
| `vslam_stereo`, `vslam_rgbd` | Isaac Sim에서 두 모드 모두 시각 오도메트리 메시지를 발행했습니다. 기본 설정은 기존 주행 스택이 map·odom TF를 계속 담당합니다. |
| `nvblox` | 정렬 깊이와 카메라 보정값으로 폭 64셀의 `/nvblox_node/static_map_slice`를 발행했습니다. |
| `pointcloud`, `xyzrgb` | 640×480 영상에서 각각 307,200점을 생성합니다. 출력은 `/waffle/points`, `/waffle/points_rgb`입니다. |
| `resize`, `crop`, `flip`, `rectify` | 앞의 두 프로필에서 320×240, 뒤의 두 프로필에서 640×480 출력을 확인했습니다. |
| `apriltag` | 검출 배열 발행을 확인했습니다. 알려진 마커에 대한 자세 오차는 추가 측정이 필요합니다. |
| `h264` | `/waffle/h264`에 압축 프레임을 발행합니다. 데스크톱에서는 NVIDIA V4L2 플러그인 설치 여부에 따라 네이티브 인코더 또는 PyAV NVENC를 선택합니다. `h264_backend:=isaac` 또는 `nvenc`로 지정할 수 있습니다. 시험 사진과 `input_qos:=RELIABLE`에서 109,684바이트의 H.264 메시지를 수신했습니다. |

Nav2에서는 `navigation.launch.py nvblox:=true`가 기존 LDS 장애물 레이어와 함께 로컬 costmap에 nvblox 슬라이스를 추가합니다. mock 주행 스택에서 플러그인 초기화와 구독 토픽을 확인했습니다. cuMotion에 3D 장애물을 공급하려면 nvblox에 `esdf_mode:=3d`, cuMotion에 `use_esdf:=true`, 아래 계획 클라이언트에 `--use-esdf`를 줍니다. 동적 장애물 회피 성능은 별도 검증 대상입니다.

## OpenMANIPULATOR-X 궤적 계획

```bash
python3 tools/export_urdf.py ../simulation/waffle.urdf
python3 isaac_ros/prepare_planner.py ../simulation/waffle.urdf ../simulation/planner --aperture-joint .01
ros2 launch turtlebot3_manipulation_bringup gpu.launch.py profile:=cumotion
# 같은 환경의 두 번째 터미널
python3 isaac_ros/cumotion_plan.py
~/isaacsim6_venv/bin/python isaac_ros/curobo_plan.py ../simulation/planner --goal .18 -.1 .12 0
```

모델은 차체와 그리퍼를 지정한 자세에 고정하고 팔 4축을 계획합니다. 그리퍼 개방량이 바뀌면 해당 자세에 맞는 모델을 다시 생성합니다. cuRobo에서는 `--scene`으로 차체 기준 월드 YAML을 줄 수 있습니다. 독립 실행에서 cuMotion 39점, cuRobo 46점 경로를 확인했습니다. 작동 중인 cuMotion 서버와 로봇 컨트롤러에 `ros2 launch turtlebot3_manipulation_moveit_config move_group.launch.py cumotion:=true`를 추가하면 MoveIt에서도 쓸 수 있습니다. 파이프라인 ID는 `isaac_ros_cumotion`, 플래너는 `cuMotion`입니다. mock 컨트롤러에서 31점 계획과 실행이 성공했습니다.

## GPU 추론과 NVIDIA 예제

다음 예제는 HF에서 고정된 ONNX를 내려받아 해당 GPU용 TensorRT 엔진을 빌드합니다. 카메라가 없는 별도 로컬 도메인에서 학습 예제의 웹 사진을 카메라 입력으로 재생할 수 있습니다.

```bash
RUN="$HOME/waffle_mpx/learning_runs"
~/IsaacLab/.venv/bin/python isaac_ros/prepare_yolo.py "$RUN/yolov8n.plan"
ros2 launch turtlebot3_manipulation_bringup yolo.launch.xml engine:="$RUN/yolov8n.plan"
# 같은 환경의 두 번째 터미널
python3 isaac_ros/probe_image.py "$HOME/waffle_mpx/learning_runs/hf-examples/web/00000.jpg"
```

시험 사진에서 개 두 마리가 COCO 클래스 16으로 검출됐고 신뢰도는 0.792와 0.781이었습니다.

`packages.txt`는 FoundationStereo·ESS, FoundationPose·DOPE, Grounding DINO·RT-DETR, SAM·SegFormer, Triton, 데이터 수집 등 42개 패키지를 지정합니다. `python3 isaac_ros/catalog.py`는 이 PC에서 발견한 launch 파일, 컴포넌트와 fragment 이름을 출력합니다. 카메라를 연결하려면 `gpu_example.launch.py`에 목록에 나온 `package:=패키지 file:=파일명` 또는 `fragments:=이름`을 주고 `streams:=rgb`, `stereo`, `depth`를 쉼표로 조합합니다. fragment의 인터페이스 명세는 `specs:=경로`로 교체할 수 있습니다. 개별 모델은 해당 예제의 엔진, 클래스 설정, 객체 메시·마스크 또는 지도 같은 입력을 준비해야 합니다. 위 표와 YOLO 이외의 모델별 정확도와 실행 결과는 아직 확인하지 않았습니다.
