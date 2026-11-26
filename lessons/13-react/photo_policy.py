"""Score discrete camera actions with the pretrained SmolVLM2 language head."""
import json
import sys

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

MODEL = "HuggingFaceTB/SmolVLM2-500M-Video-Instruct"
REV = "4cde9d208e19519c36917aa170fffc7e381aa0ad"
image, measured, limit = sys.argv[1:]
distance, threshold = float(measured), float(limit)
processor = AutoProcessor.from_pretrained(MODEL, revision=REV)
processor.image_processor.do_image_splitting = False
device = "cuda" if torch.cuda.is_available() else "cpu"
model = AutoModelForImageTextToText.from_pretrained(MODEL, revision=REV, dtype=torch.float16 if device=="cuda" else torch.float32).to(device).eval()
message = f"The task is to take a photo of the scene if an object is within {threshold:g} meters. The range sensor reads {distance:.3f} meters. The distance condition is {'satisfied' if distance<=threshold else 'not satisfied'}. This is the live camera image. Should the camera save this image now to complete the task? Answer Yes or No."
conversation = [{"role":"user","content":[{"type":"image"},{"type":"text","text":message}]}]
prompt = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
inputs = processor(text=prompt, images=[Image.open(image).convert("RGB")], return_tensors="pt").to(device)
with torch.inference_mode():
    logits = model(**inputs).logits[0,-1].float()
    ids = [processor.tokenizer.encode(word,add_special_tokens=False) for word in ("Yes","No")]
    if any(len(x)!=1 for x in ids):
        raise RuntimeError("Unexpected action tokenization")
    scores = logits[[x[0] for x in ids]].tolist()
# Limit is a hard precondition. The model can still decline a permitted photo.
action = "capture" if scores[0]>scores[1] and distance<=threshold else "skip"
print(json.dumps({"action":action,"yes_logit":scores[0],"no_logit":scores[1],"range_allowed":distance<=threshold}))
