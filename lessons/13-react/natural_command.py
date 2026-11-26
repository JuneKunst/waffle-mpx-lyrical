"""Run a Korean request through a local LLM and the Isaac photo or arm policy."""
import argparse
import json
import math
import os
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODEL = "qwen2.5:1.5b"
SYSTEM = """Translate the Korean robot request into one intent. photo means conditional camera capture; convert its distance from centimeters or meters to meters. drive means move the base straight forward by the stated distance, convert it to meters. pick_red / pick_blue mean pick the named cube and place it on the green square. For unsupported goals, multiple actions, missing color for picking, or missing photo threshold choose unsupported. Examples: '20센티미터 안이면 사진 찍어줘' -> photo with meters 0.2; '파란 블록을 초록 칸에 놓아줘' -> pick_blue. For pick or unsupported use meters 0."""
def interpret(sentence):
    schema = {"type":"object","properties":{"intent":{"type":"string","enum":["photo","pick_red","pick_blue","drive","unsupported"]},"meters":{"type":"number"}},"required":["intent","meters"]}
    payload = {"model":MODEL,"stream":False,"keep_alive":0,"format":schema,"options":{"temperature":0,"num_predict":64,"num_ctx":2048},"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":sentence}]}
    req=Request("http://127.0.0.1:11434/api/chat",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urlopen(req,timeout=120) as response:
        plan=json.loads(json.load(response)["message"]["content"])
    if plan.get("intent") not in schema["properties"]["intent"]["enum"] or type(plan.get("meters")) not in (float,int):
        raise ValueError("Invalid model output")
    return plan

def photo(limit,output):
    import rclpy
    from sensor_msgs.msg import Image,LaserScan
    from rclpy.qos import qos_profile_sensor_data
    rclpy.init()
    node=rclpy.create_node("lesson13_model_case")
    latest={}
    node.create_subscription(Image,"/camera/color/image_raw",lambda m:latest.update(rgb=m),qos_profile_sensor_data)
    node.create_subscription(LaserScan,"/scan",lambda m:latest.update(scan=m),qos_profile_sensor_data)
    try:
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.1)
            if len(latest)==2:
                def stamp(m):return m.header.stamp.sec+m.header.stamp.nanosec/1e9
                if abs(stamp(latest["rgb"])-stamp(latest["scan"]))<=.15: break
        else: raise RuntimeError("Timed out waiting for matching camera and lidar samples")
        rgb,scan=latest["rgb"],latest["scan"]
    finally:
        node.destroy_node()
        rclpy.shutdown()
    hits=[x for x in scan.ranges if math.isfinite(x) and scan.range_min<=x<=scan.range_max]
    if not hits or rgb.encoding!="rgb8":raise RuntimeError("Invalid sensor observation")
    from PIL import Image as PILImage
    img=PILImage.frombytes("RGB",(rgb.width,rgb.height),bytes(rgb.data),"raw","RGB",rgb.step)
    with tempfile.TemporaryDirectory() as temp:
        observation=Path(temp)/"rgb.png"
        img.save(observation)
        env=os.environ.copy()
        env["PYTHONPATH"]=env.get("WAFFLE_LEARNING_DEPS",str(ROOT.parent/".learning-deps"))
        lab=os.environ.get("ISAAC_LAB_PYTHON",str(Path.home()/"IsaacLab/.venv/bin/python"))
        result=subprocess.check_output([lab,str(HERE/"photo_policy.py"),str(observation),str(min(hits)),str(limit)],env=env,text=True)
    decision=json.loads(result)
    if decision["action"]=="capture": img.save(output/"photo.png")
    return dict(distance_m=min(hits),threshold_m=limit,**decision)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--scene",type=Path,default=Path(os.environ.get("WAFFLE_SCENE", ROOT.parent/"simulation/scene.usda")))
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--show",action="store_true")
    args=p.parse_args()
    sentence=input("자연어 명령 > ").strip()
    plan=interpret(sentence)
    print("LLM",json.dumps(plan,ensure_ascii=False),flush=True)
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/"request.json").write_text(json.dumps({"request":sentence,"model":MODEL,"plan":plan},ensure_ascii=False,indent=2))
    if plan["intent"]=="photo" and 0<plan["meters"]<=12:
        outcome=photo(plan["meters"],args.output)
    elif plan["intent"]=="drive" and 0<plan["meters"]<=.15:
        from drive_feedback import advance
        outcome=advance(plan["meters"])
    elif plan["intent"] in ("pick_red","pick_blue"):
        target=plan["intent"].split("_")[1]
        sim=os.environ.get("ISAAC_SIM_PYTHON",str(Path.home()/"isaacsim6_venv/bin/python"))
        ckpt=ROOT/"learning/checkpoints"
        run=args.output/"physics"
        cmd=[sim,str(ROOT/"sim/evaluate_pick_place.py"),str(args.scene.resolve()),str(ckpt/"waffle-color-73.npz"),str(run),"--controller","color","--parent-vla",str(ckpt/"waffle-hf-vla.pt"),"--target",target,"--layouts","1","--seed","8601","--decisions","92","--record-frames"]
        if args.show:cmd.append("--show")
        print("VLA → Isaac Sim · "+target+" · 92개 목표를 실행합니다.",flush=True)
        with (args.output/"isaac.log").open("w") as log:
            subprocess.run(cmd,check=True,stdout=log,stderr=subprocess.STDOUT)
        outcome=json.loads((run/"results.json").read_text())["results"][0]
    else: raise SystemExit("지원하지 않는 작업 또는 거리입니다.")
    (args.output/"outcome.json").write_text(json.dumps(outcome,ensure_ascii=False,indent=2))
    print("RESULT",json.dumps(outcome,ensure_ascii=False))
if __name__=="__main__":main()
