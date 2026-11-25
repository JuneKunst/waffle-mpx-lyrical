# 설치와 첫 실행

로봇 없이 시작하려면 제어 PC에서 1–3절을 실행한다. 실제 로봇을 쓸 때는 Pi에서도 워크스페이스를 빌드하고 4절로 진행한다. Isaac 학습 실습은 NVIDIA GPU PC에서 5–6절을 추가로 실행한다.

## 1. 운영체제와 ROS 설치

| 장치 | 설치 기준 | 설치 전 확인 |
|---|---|---|
| Raspberry Pi | 해당 Pi 기종을 지원하는 Ubuntu Server 26.04 LTS arm64 + ROS 2 Lyrical | `uname -m`이 `aarch64`인지 확인한다. SSH, USB 3, OpenCR·LDS용 시리얼 연결을 준비한다. |
| 제어 PC | Lyrical을 설치한 Ubuntu, Bash, RViz용 디스플레이 | ROS 기본 환경과 개발 도구를 설치한다. |
| GPU PC | 검증 환경은 Ubuntu 24.04 amd64, NVIDIA Lyrical, RTX 5060 Laptop GPU, Isaac Sim 6.1, Python 3.12 | `nvidia-smi`에서 GPU를 확인한다. ROS Python과 Isaac Sim Python의 ABI가 일치해야 한다. |

26.04 호스트에는 ROS 공식 Ubuntu 설치 안내의 저장소와 서명 키를 등록한다. 24.04 GPU 호스트에는 NVIDIA Isaac ROS 5의 **x86 Ubuntu Noble** 절차로 Lyrical 기본 패키지 저장소와 release-5.0 저장소를 등록한다. 배포판별 저장소를 설정한 뒤 아래를 실행한다. [ROS 2 Lyrical 설치](https://docs.ros.org/en/lyrical/Installation/Ubuntu-Install-Debs.html) · [NVIDIA Isaac ROS 5 설치](https://nvidia-isaac-ros.github.io/v/release-5.0/getting_started/index.html)

```bash
sudo apt update
sudo apt install git build-essential cmake ros-dev-tools ros-lyrical-ros-base
source /opt/ros/lyrical/setup.bash
echo "$ROS_DISTRO"
```

## 2. 클론과 빌드

아래는 새 워크스페이스 기준이다. 저장소 루트에 ROS 패키지들이 있으므로 `src` 자체를 클론 대상으로 사용한다. 기존 체크아웃이 있다면 해당 디렉터리를 사용한다.

```bash
mkdir -p ~/waffle_mpx
git clone https://github.com/SpartaPA/waffle-mpx-lyrical.git ~/waffle_mpx/src
cd ~/waffle_mpx
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then sudo rosdep init; fi
rosdep update
rosdep install --from-paths src --ignore-src --rosdistro lyrical -y
colcon list --names-only
colcon build --symlink-install --parallel-workers 2 --cmake-args -DBUILD_TESTING=OFF
source src/tools/lyrical_env.bash
ros2 pkg prefix turtlebot3_manipulation_bringup
```

`colcon list`에는 [동봉 패키지 8개](packages.md)가 표시된다. Cartographer 빌드 시 `map_builder.lua`, `lua.hpp`, `cartographer_ros/node.h`가 필요하다. 설치 실패 시 `apt-cache policy ros-lyrical-cartographer ros-lyrical-cartographer-ros ros-lyrical-cartographer-ros-msgs`로 해당 OS의 후보 버전을 확인하고, Lua 개발 헤더와 Cartographer 패키지를 설치한다. GPU 호스트에서 검증한 Lua 개발 패키지는 `liblua5.2-dev`다.

## 3. 하드웨어 없이 제어 확인

각 터미널에서 `source ~/waffle_mpx/src/tools/lyrical_env.bash`와 `export ROS_DOMAIN_ID=42`를 실행한다.

```bash
# 터미널 1
ros2 launch turtlebot3_manipulation_bringup robot.launch.py mode:=mock

# 터미널 2
ros2 control list_controllers
ros2 topic echo /joint_states --once
ros2 launch turtlebot3_manipulation_moveit_config move_group.launch.py
```

컨트롤러가 `active`인지 확인한 뒤 RViz의 **MotionPlanning → arm → Plan & Execute**로 관절 상태 변화를 확인한다. [텔레옵 키, 지도 작성, 지도 저장, Nav2 실행 순서](../README.md#주행과-조작)

## 4. 실물 전환

1. [D435 조립 도면](../design/README.md)과 OpenCR manipulation 펌웨어를 확인한다. 초기 자세로 움직일 수 있으므로 팔 주변을 비운다.
2. Pi에서 `sudo usermod -aG dialout "$USER"` 후 다시 로그인한다. `ls -l /dev/serial/by-id/ /dev/serial/by-path/`로 OpenCR와 LDS 포트를 구별하고 D435는 USB 3에 연결한다.
3. Pi에서 아래 launch를 실행한다. 장치 경로를 확인한 값으로 바꾼다. 같은 LAN의 제어 PC는 Pi와 같은 ROS 도메인을 사용한다.

```bash
ros2 launch turtlebot3_manipulation_bringup robot.launch.py mode:=hardware \
  opencr_port:=/dev/ttyACM0 lidar_port:=/dev/ttyUSB0
# 제어 PC
ros2 topic hz /scan
ros2 topic hz /camera/color/image_raw
ros2 control list_controllers
```

## 5. Isaac Sim과 Isaac Lab 설치

검증한 GPU 호스트에서는 Sim과 Lab을 각각 별도 Python 환경에 설치했다. Sim은 Python 3.12 가상환경을 만들어 공식 6.1 패키지를 설치한다. 처음 시작할 때 NVIDIA 라이선스 확인과 확장 패키지 다운로드가 필요할 수 있다. [Isaac Sim Python 설치](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/installation/install_python.html)

```bash
python3.12 -m venv ~/isaacsim6_venv
~/isaacsim6_venv/bin/python -m pip install --upgrade pip
~/isaacsim6_venv/bin/python -m pip install 'isaacsim[all,extscache]==6.1.0.0' --extra-index-url https://pypi.nvidia.com
```

Isaac Lab은 [3.0 설치 문서](https://isaac-sim.github.io/IsaacLab/v3.0.0-EA/source/setup/installation/index.html)의 Newton 환경을 설치한다. 예제는 기본적으로 `~/IsaacLab/.venv/bin/python`을 사용한다. 다른 경로라면 `ISAAC_LAB_PYTHON`에 해당 Python의 절대 경로를 지정한다. Isaac Sim과 ROS를 함께 실행하기 전에 아래 import를 확인한다.

```bash
cd ~/waffle_mpx
source src/tools/lyrical_env.bash
export ROS_DOMAIN_ID=43
export PYTHONPATH="$PYTHONPATH:/usr/lib/python3/dist-packages"
~/isaacsim6_venv/bin/python -c 'import rclpy; from sensor_msgs.msg import Image'
mkdir -p simulation
python3 src/tools/export_urdf.py simulation/waffle.urdf
~/isaacsim6_venv/bin/python src/sim/scene.py simulation/waffle.urdf --output simulation --headless --steps 5
```

성공하면 `simulation/scene.usda`와 `simulation/waffle.usda`가 생긴다. 텔레옵·SLAM 실습에서는 `--steps 5`를 빼고 시뮬레이터를 계속 실행한다. 두 번째 터미널에서 같은 도메인으로 `robot.launch.py mode:=isaac`를 실행한다. [시뮬레이터 제어 순서](../README.md#isaac-sim-61과-isaac-lab) · [Isaac ROS GPU 패키지와 실행 예](../isaac_ros/README.md)

## 6. 배포 체크포인트로 색상 집기 평가

체크포인트 두 개는 학습된 행동 헤드와 궤적 예측층이다. 처음 한 번 인터넷에 연결해 지정된 Hugging Face 시각·언어 백본을 받아야 한다. 아래는 GPU 호스트에서 5절을 완료한 상태를 전제로 한다. 기본 ROS와 Sim 설정이 끝났다면 이 평가에는 실물 로봇이 필요하지 않다.

```bash
cd ~/waffle_mpx/src
LAB="${ISAAC_LAB_PYTHON:-$HOME/IsaacLab/.venv/bin/python}"
"$LAB" -m pip install -r learning/requirements.txt matplotlib
(cd learning/checkpoints && sha256sum -c SHA256SUMS)
RUN="$HOME/waffle_mpx/learning_runs"
mkdir -p "$RUN"
OUT="$RUN/public-eval-$(date +%Y%m%d-%H%M%S)"
export ISAAC_LAB_PYTHON="$LAB"
~/isaacsim6_venv/bin/python sim/evaluate_pick_place.py ../simulation/scene.usda \
  learning/checkpoints/waffle-color-73.npz "$OUT" --controller color \
  --parent-vla learning/checkpoints/waffle-hf-vla.pt --layouts 4 --seed 8601 --decisions 92
python3 learning/audit_color_eval.py learning/checkpoints/waffle-color-73.npz "$OUT"
"$LAB" learning/plot_pick_place.py "$OUT" "$OUT/paired-trial.png" --layout 0
```

[데이터 다운로드와 HF 정책 학습](../learning/README.md) · [색상별 시연 생성과 재학습](../learning/color-pick-place.md) · [배포 모델의 8회 평가 기록](../learning/color-heldout-8601.json)
