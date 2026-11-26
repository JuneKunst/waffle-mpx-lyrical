# 13강 · ReAct와 Tool Use
라이다 최솟값이 사용자가 지정한 거리 이내이면 D435 사진을 저장합니다. 실행 코드와 예제 결과는 모두 이 GitHub 폴더에 있습니다.

## GitHub에서 실습 받기

새 GPU PC에서는 다음 명령으로 저장소를 받습니다.

    mkdir -p ~/waffle_mpx
    git clone https://github.com/SpartaPA/waffle-mpx-lyrical.git ~/waffle_mpx/src

이미 같은 저장소를 사용한다면 main 브랜치에서 다음 명령으로 업데이트합니다.

    git -C ~/waffle_mpx/src pull --ff-only

[설치 안내](../../docs/install.md)에 따라 ROS 2 Lyrical 워크스페이스와 Isaac Sim 6.1을 준비합니다.

## 준비 1 · 사용할 모델과 소프트웨어

| 과정 | 모델과 가중치 | 입력과 출력 |
|---|---|---|
| 13강 터미널 명령 해석 | LLM 사용 없음. [natural_command.py](natural_command.py)의 Python 정규식으로 지정된 한국어 촬영 문형을 읽습니다. | 문장에서 거리와 단위를 추출하고 미터로 환산합니다. |
| 13강 도구 선택 | VLA 사용 없음. [waffle_react.py](waffle_react.py)의 조건문과 등록된 도구 두 개를 사용합니다. | 유효한 라이다 거리와 예산으로 사진 저장 또는 종료를 선택합니다. |
| 선택 실습 · 로봇 행동 예측 | 고정한 [SmolVLM2-500M-Video-Instruct 인코더](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct/tree/4cde9d208e19519c36917aa170fffc7e381aa0ad)와 Waffle용 행동 예측층을 사용합니다. | D435 RGB 한 장, 언어 지시, 로봇 상태 7개를 받아 차체·팔·그리퍼 명령 7개를 예측합니다. |

촬영 실습에는 ROS 2 Lyrical의 rclpy·sensor_msgs, Isaac Sim 6.1과 이를 실행할 GPU가 필요합니다. 촬영 실습은 API 키와 모델 다운로드 없이 실행합니다. 선택 VLA 실습용 PyTorch 환경과 가중치 준비 절차는 [학습 안내](../../learning/README.md)에 있습니다.

## 준비 2 · 촬영 실습의 아키텍처

1. **명령 해석** — 터미널에서 “20센티미터 이내에 물체가 있으면 사진을 한 장 저장해 주세요.”라고 입력하면 실행기에 임계값 0.2m가 전달됩니다.
2. **센서 조회** — Isaac Sim의 [ROS 인터페이스](../../sim/ros_io.py)가 /scan을 발행합니다. read_scan은 유효한 거리의 최솟값과 프레임, 시뮬레이션 시각을 반환합니다.
3. **분기** — 거리 ≤ 임계값이고 호출 예산이 남으면 take_photo를 선택합니다. 임계값을 초과하면 outside_threshold, 예산이 소진되면 budget_exhausted로 끝납니다.
4. **저장 및 확인** — take_photo가 /camera/color/image_raw에서 RGB를 받아 PPM으로 저장합니다. 터미널에는 도구 이름, 관측값과 최종 종료 사유가 남습니다.

## 준비 3 · 선택 VLA 예제의 아키텍처

[policy.py](../../learning/policy.py)의 VLA는 RGB와 지시문에서 얻은 SmolVLM2 마지막 토큰 특징에 정규화한 로봇 상태 7개를 연결합니다. LayerNorm → 128차원 선형층 → SiLU → 출력층을 거쳐 7개 행동 축 각각에 대해 257개 구간 중 하나를 선택합니다. 행동 축은 차체 전진·회전, 팔 관절 4개와 그리퍼입니다.

[배포 체크포인트](../../learning/checkpoints/waffle-hf-vla.pt)는 Waffle 행동 예측층을 담습니다. 인코더는 Hugging Face의 고정 리비전 4cde9d2에서 불러옵니다. 이 예제는 RT-2의 이산 행동 표현을 참고해 구현했습니다. 별도 [색상 집기 예제](../../learning/color-pick-place.md)는 고정한 128차원 특징과 색상 위치·크기를 결합해 92개 시점의 관절·그리퍼 목표를 회귀합니다.

## 터미널 A · Isaac Sim 6.1
아래 명령은 강의용 로컬 도메인 113을 사용합니다. 같은 PC에서 모든 터미널을 엽니다.

    cd ~/waffle_mpx
    source src/tools/lyrical_env.bash
    export ROS_DOMAIN_ID=113 ROS_LOCALHOST_ONLY=1
    mkdir -p simulation/lesson13
    python3 src/tools/export_urdf.py simulation/lesson13/waffle.urdf
    PYTHONPATH="$PYTHONPATH:/usr/lib/python3/dist-packages" ~/isaacsim6_venv/bin/python src/sim/scene.py simulation/lesson13/waffle.urdf --output simulation/lesson13

창 없이 실행하려면 마지막 명령에 --headless를 붙입니다. 실습을 마치면 Ctrl+C로 종료합니다.

## 터미널 B · GitHub 실습 폴더에서 실행

    cd ~/waffle_mpx/src/lessons/13-react
    source ~/waffle_mpx/src/tools/lyrical_env.bash
    export ROS_DOMAIN_ID=113 ROS_LOCALHOST_ONLY=1
    ros2 topic info /scan
    python3 waffle_react.py --threshold 1.5
    python3 waffle_react.py --threshold 0.2
    python3 waffle_react.py --budget 1
    python3 waffle_react.py --first-tool locate_cup
    ROS_DOMAIN_ID=112 python3 waffle_react.py --timeout 2

실행할 때마다 turn/tool/observation과 정지 사유가 JSON 줄로 출력됩니다. 첫 실행에서 생성하는 waffle.ppm을 이미지 뷰어로 열어봅니다. 같은 이름의 사진은 덮어쓰므로 비교하려면 --image run2.ppm처럼 이름을 지정합니다. timeout 시험은 도메인 112에 같은 토픽의 발행자가 없다고 가정합니다. measured.jsonl은 위 네 실험의 실측 로그이고, timeout.jsonl은 다섯 번째 실험의 로그입니다. [camera.png](media/camera.png)는 첫 실험에서 저장한 RGB 프레임입니다.

두 도구는 센서 조회와 사진 저장을 수행합니다. 정책은 관측 거리와 임계값으로 다음 도구를 선택하는 Python 규칙입니다. LLM 키나 주행 컨트롤러는 필요하지 않습니다. 라이다 최솟값은 360도 전방위 결과이므로 카메라 영상만으로 그 물체의 신원을 확정할 수 없습니다.

## 한국어로 조건 입력하기

터미널 B에서 실행합니다.

    python3 natural_command.py --image near.ppm

프롬프트에 다음 문장을 입력하고 Enter를 누릅니다.

    1.5미터 안에 물체가 있으면 사진을 찍어 줘.

다시 실행할 때는 파일명을 far.ppm으로 바꾸고 다음 문장을 입력합니다.

    20센티미터 이내에 물체가 있으면 사진을 한 장 저장해 주세요.

입력기는 거리와 촬영 요청을 지정된 한국어 문형으로 해석합니다. 지원 단위는 m, 미터, cm, 센티미터입니다. 녹화 환경에서는 두 터미널 모두 도메인 114를 사용했습니다.

| 실습 | 영상 | 터미널 캡처 |
|---|---|---|
| 1.5m · 사진 저장 | [영상 보기](media/near.mp4) | [입력](media/near-input.png) · [결과](media/near-result.png) |
| 20cm · 촬영 생략 | [영상 보기](media/far.mp4) | [입력](media/far-input.png) · [결과](media/far-result.png) |
| 예산 소진 · 미등록 도구 · 시간 초과 | [영상 보기](media/errors.mp4) | [결과](media/errors-result.png) |

복제한 폴더에서 영상은 로컬 플레이어로도 열 수 있습니다. 예를 들어 다음 명령으로 첫 영상을 재생합니다.

    xdg-open media/near.mp4
