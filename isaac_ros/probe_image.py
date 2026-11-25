"""Send a fixture on D435 topics in a test domain and verify a GPU output."""
import argparse
import time
import rclpy
from PIL import Image as Pillow
from sensor_msgs.msg import CameraInfo, Image, CompressedImage
from vision_msgs.msg import Detection2DArray

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('image')
p.add_argument('--profile',choices=['yolo','h264'],default='yolo')
args=p.parse_args()
rclpy.init()
node=rclpy.create_node('waffle_image_fixture')
with Pillow.open(args.image) as photo:
    image=Image(height=480,width=640,encoding='rgb8',step=1920,
                data=photo.convert('RGB').resize((640,480)).tobytes())
info=CameraInfo(width=640,height=480,k=[500.,0.,320.,0.,500.,240.,0.,0.,1.],
                p=[500.,0.,320.,0.,0.,500.,240.,0.,0.,0.,1.,0.])
images=node.create_publisher(Image,'/camera/color/image_raw',3)
calibration=node.create_publisher(CameraInfo,'/camera/color/camera_info',3)
seen=[]
def detections(msg):
    seen.extend((r.hypothesis.class_id,round(r.hypothesis.score,3)) for d in msg.detections for r in d.results)
def compressed(msg):
    if msg.data:seen.append((msg.format,len(msg.data)))
if args.profile=='yolo':node.create_subscription(Detection2DArray,'/detections_output',detections,10)
else:node.create_subscription(CompressedImage,'/waffle/h264',compressed,10)
deadline=time.monotonic()+40
try:
    while not seen and time.monotonic()<deadline:
        image.header.stamp=node.get_clock().now().to_msg();image.header.frame_id='camera_color_optical_frame'
        info.header=image.header;images.publish(image);calibration.publish(info)
        rclpy.spin_once(node,timeout_sec=.15)
finally:
    node.destroy_node();rclpy.try_shutdown()
if not seen:raise SystemExit('No matching GPU output within 40 seconds')
print(args.profile,seen)
