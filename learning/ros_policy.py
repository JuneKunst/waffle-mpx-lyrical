"""Record an RGB teleoperation episode or run a Waffle policy on live ROS topics."""
import argparse
from collections import deque
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image as PILImage
import message_filters
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TwistStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from actions import JOINTS, NAMES, LOW, HIGH, SCHEMA

def seconds(stamp):
    return stamp.sec+stamp.nanosec*1e-9


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--record',type=Path);mode.add_argument('--policy',type=Path)
    parser.add_argument('--instruction',required=True)
    parser.add_argument('--trace',type=Path,help='Write observations, predicted and applied commands as JSONL')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--frames',type=int,default=0)
    parser.add_argument('--hz',type=float,default=5.)
    parser.add_argument('--device',default='cuda')
    args,ros_args=parser.parse_known_args()
    if args.hz<=0 or (args.execute and not args.policy):parser.error('Check --hz and --execute')
    policy=None; out=None
    if args.policy:
        from policy import Policy
        policy=Policy(args.policy,args.device)
    else:
        args.record.mkdir(parents=True,exist_ok=False)
        (args.record/'episode.json').write_text(json.dumps(dict(schema=SCHEMA,instruction=args.instruction,
            state=NAMES,action=NAMES),ensure_ascii=False,indent=2))
        out=(args.record/'frames.jsonl').open('x',buffering=1)
    rclpy.init(args=ros_args)
    node=rclpy.create_node('waffle_learning')
    def now():return node.get_clock().now().nanoseconds*1e-9
    base_history=deque(maxlen=256)
    joint_history={name:deque(maxlen=256) for name in JOINTS}
    def base_cmd(msg):
        base_history.append((seconds(msg.header.stamp),[msg.twist.linear.x,msg.twist.angular.z]))
    def joint_cmd(msg):
        if len(msg.points)!=1:return
        for name,q in zip(msg.joint_names,msg.points[0].positions):
            if name in joint_history: joint_history[name].append((now(),q))
    node.create_subscription(TwistStamped,'cmd_vel',base_cmd,10)
    for controller in ['arm_controller','gripper_controller']:
        node.create_subscription(JointTrajectory,controller+'/joint_trajectory',joint_cmd,10)
    def latest(series,t,age,default):
        return next((v for ts,v in reversed(series) if 0<=t-ts<=age),default)
    base=node.create_publisher(TwistStamped,'cmd_vel',1)
    def drive(values):
        cmd=TwistStamped()
        cmd.header.stamp=node.get_clock().now().to_msg()
        cmd.twist.linear.x,cmd.twist.angular.z=map(float,values)
        base.publish(cmd)
    arm=node.create_publisher(JointTrajectory,'arm_controller/joint_trajectory',1)
    grip=node.create_publisher(JointTrajectory,'gripper_controller/joint_trajectory',1)
    shadow=node.create_publisher(JointState,'learning/predicted_action',1)
    trace=args.trace.open('x',buffering=1) if args.trace else None
    last=-np.inf; count=0
    def sample(im,joints,odom):
        nonlocal last,count
        t=seconds(im.header.stamp)
        if t<last: raise RuntimeError('ROS clock reset during episode')
        if t-last<1/args.hz-.001:return
        q=dict(zip(joints.name,joints.position))
        if any(k not in q for k in JOINTS):return
        twist=odom.twist.twist
        state=np.array([twist.linear.x,twist.angular.z,*[q[k] for k in JOINTS]])
        if not np.isfinite(state).all():return
        if im.encoding not in ('rgb8','bgr8'):raise ValueError(f'Unsupported RGB encoding {im.encoding}')
        rgb=np.frombuffer(im.data,np.uint8).reshape(im.height,im.step)[:,:im.width*3].reshape(im.height,im.width,3)
        image=PILImage.fromarray(rgb if im.encoding=='rgb8' else rgb[:,:,::-1])
        if out:
            target=latest(base_history,t,.5,[0.,0.])+[latest(joint_history[k],t,np.inf,q[k]) for k in JOINTS]
            if not np.isfinite(target).all():return
            name=f'{count:07d}.jpg'
            image.save(args.record/name,quality=90)
            out.write(json.dumps(dict(time=t,image=name,state=state.tolist(),action=target))+'\n')
        else:
            start=time.monotonic()
            action=policy.predict(image,args.instruction,state)
            if np.shape(action)!=(7,) or not np.isfinite(action).all():raise ValueError('Invalid predicted action')
            shadow.publish(JointState(header=im.header,name=NAMES,position=action.astype(float).tolist()))
            sent=None
            latency=time.monotonic()-start
            age=now()-t
            if args.execute:
                if latency>.45 or not -.1<=age<.45:
                    drive([0,0])
                else:
                    action=np.clip(action,LOW,HIGH)
                    drive(action[:2])
                    max_step=np.array([.35]*4+[.012])/args.hz
                    targets=(state[2:]+np.clip(action[2:]-state[2:],-max_step,max_step)).tolist()
                    sent=action[:2].tolist()+targets
                    for pub,names,values in [(arm,JOINTS[:4],targets[:4]),(grip,JOINTS[4:],targets[4:])]:
                        pub.publish(JointTrajectory(joint_names=names,points=[JointTrajectoryPoint(
                            positions=values,time_from_start=Duration(nanosec=250000000))]))
            if trace:
                trace.write(json.dumps(dict(time=t,state=state.tolist(),predicted=action.tolist(),applied=sent,inference_s=latency,stamp_age_s=age))+'\n')
        count+=1;last=t
    subs=[message_filters.Subscriber(node,typ,topic,qos_profile=qos_profile_sensor_data) for typ,topic in
          [(Image,'camera/color/image_raw'),(JointState,'joint_states'),(Odometry,'odom')]]
    sync=message_filters.ApproximateTimeSynchronizer(subs,queue_size=15,slop=.10)
    sync.registerCallback(sample)
    try:
        while rclpy.ok() and (not args.frames or count<args.frames):rclpy.spin_once(node,timeout_sec=.5)
    except KeyboardInterrupt:
        pass
    finally:
        if args.execute and rclpy.ok():drive([0,0])
        if out:out.close()
        if trace:trace.close()
        node.destroy_node();rclpy.try_shutdown()
        print(f'{count} synchronized frames')

if __name__=='__main__': main()
