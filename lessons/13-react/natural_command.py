"""13강에서 사용하는 거리 조건부 촬영 명령을 ROS 실행기에 전달합니다."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--budget", type=int, default=2)
parser.add_argument("--image", default="waffle.ppm")
options = parser.parse_args()
sentence = input("자연어 명령 > ").strip()
pattern = (r"(\d+(?:\.\d+)?)\s*(m|미터|cm|센티미터)\s*"
           r"(?:안에|이내에)\s*물체가\s*있으면\s*사진을\s*(?:한\s*장\s*)?"
           r"(?:찍어\s*(?:줘|주세요)|저장해\s*(?:줘|주세요))[.!]?")
match = re.fullmatch(pattern, sentence, re.IGNORECASE)
if not match:
    parser.exit(2, "지원하는 예문: 1.5미터 안에 물체가 있으면 사진을 찍어 줘.\n")
distance = float(match[1]) / (100 if match[2].lower() in ("cm", "센티미터") else 1)
if not 0 < distance <= 12 or options.budget < 0:
    parser.exit(2, "거리는 0m 초과 12m 이하, 예산은 0 이상으로 입력합니다.\n")
print(f"조건: 최근접 거리 ≤ {distance:g} m   |   행동: 사진 저장   |   예산: {options.budget}", flush=True)
script = Path(__file__).resolve().with_name("waffle_react.py")
sys.exit(subprocess.run([sys.executable, str(script), "--threshold", str(distance),
                         "--budget", str(options.budget), "--image", options.image]).returncode)
