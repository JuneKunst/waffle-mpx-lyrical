"""Waffle MPX 실습. 시뮬레이터에서 새 ROS 메시지를 받아 판단합니다."""
import argparse
import json
import math
import time
from pathlib import Path

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, LaserScan

p = argparse.ArgumentParser()
p.add_argument("--threshold", type=float, default=1.5)
p.add_argument("--budget", type=int, default=2)
p.add_argument("--timeout", type=float, default=8)
p.add_argument("--image", default="waffle.ppm")
p.add_argument("--first-tool", default="read_scan")
args = p.parse_args()
if not (0 < args.threshold <= 12 and args.budget >= 0 and args.timeout > 0):
    p.error("threshold (0,12], budget >= 0, timeout > 0")
rclpy.init()
node = rclpy.create_node("lesson13_observer")
registry = {"read_scan": (LaserScan, "/scan"),
            "take_photo": (Image, "/camera/color/image_raw")}

def observe(tool):
    if tool not in registry:
        return {"ok": False, "error": "unknown_tool"}
    msg_type, topic = registry[tool]
    received = []
    sub = node.create_subscription(msg_type, topic, received.append, qos_profile_sensor_data)
    try:
        deadline = time.monotonic() + args.timeout
        while not received and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=min(.2, max(0., deadline-time.monotonic())))
        if not received:
            return {"ok": False, "source": topic, "error": "timeout"}
        m = received[-1]
        data = {"ok": True, "source": topic, "frame": m.header.frame_id,
                "stamp": [m.header.stamp.sec, m.header.stamp.nanosec]}
        if tool == "read_scan":
            hits = [v for v in m.ranges if math.isfinite(v) and m.range_min <= v <= m.range_max]
            if not hits:
                return {**data, "ok": False, "error": "no_valid_range"}
            data.update(nearest_m=round(min(hits), 4), rays=len(m.ranges))
        else:
            if m.encoding != "rgb8":
                return {**data, "ok": False, "error": "unexpected_encoding"}
            rows = bytes(m.data)
            with Path(args.image).open("wb") as f:
                f.write(f"P6\n{m.width} {m.height}\n255\n".encode())
                for y in range(m.height):
                    f.write(rows[y*m.step:y*m.step + 3*m.width])
            data.update(width=m.width, height=m.height, file=args.image)
        return data
    finally:
        node.destroy_subscription(sub)

tool = args.first_tool
stop = "budget_exhausted"
try:
    for turn in range(1, args.budget + 1):
        obs = observe(tool)
        print(json.dumps(dict(turn=turn, tool=tool, observation=obs), ensure_ascii=False))
        if not obs["ok"]:
            stop = obs["error"]
            break
        if tool == "take_photo":
            stop = "photo_saved"
            break
        if obs["nearest_m"] > args.threshold:
            stop = "outside_threshold"
            break
        tool = "take_photo"
    print(json.dumps({"stop": stop}))
finally:
    node.destroy_node()
    rclpy.shutdown()
