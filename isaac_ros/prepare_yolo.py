"""Build this GPU's TensorRT engine for a revision-pinned YOLOv8n ONNX model."""
import argparse
import shutil
import subprocess
from pathlib import Path
from huggingface_hub import hf_hub_download

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('output',type=Path)
args=p.parse_args()
path=hf_hub_download('salim4n/yolov8n-detect-onnx','yolov8n-onnx-web/yolov8n.onnx',
                     revision='98100409491fa67f62a2e780a4efe485b86dfd0b')
args.output.parent.mkdir(parents=True,exist_ok=True)
exe=shutil.which('trtexec') or '/usr/src/tensorrt/bin/trtexec'
subprocess.run([exe,'--onnx='+path,'--saveEngine='+str(args.output),'--skipInference'],check=True)
