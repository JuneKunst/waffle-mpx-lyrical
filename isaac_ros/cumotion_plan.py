"""Query the Waffle cuMotion action server without moving the robot."""
import argparse
import rclpy
from rclpy.action import ActionClient
from isaac_ros_cumotion_interfaces.action import MotionPlan

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--start',nargs=4,type=float,default=[0.]*4)
p.add_argument('--goal',nargs=4,type=float,default=[.18,-.1,.12,0.])
p.add_argument('--use-esdf',action='store_true',help='Request an ESDF update from nvblox')
args=p.parse_args()
rclpy.init()
node=rclpy.create_node('waffle_plan')
client=ActionClient(node,MotionPlan,'/cumotion/motion_plan')
def wait(future):
    rclpy.spin_until_future_complete(node,future,timeout_sec=60.)
    if not future.done(): raise TimeoutError('cuMotion response timed out')
    return future.result()
try:
    if not client.wait_for_server(timeout_sec=45.): raise TimeoutError('cuMotion unavailable')
    g=MotionPlan.Goal()
    g.start_state.name=g.goal_state.name=[f'joint{i}' for i in range(1,5)]
    g.start_state.position=args.start
    g.goal_state.position=args.goal
    g.update_esdf=args.use_esdf
    g.plan_cspace=True
    g.time_dilation_factor=.5
    handle=wait(client.send_goal_async(g))
    if not handle.accepted: raise RuntimeError('Goal rejected')
    result=wait(handle.get_result_async()).result
    if not result.success: raise RuntimeError(result.message)
    print('cuMotion trajectory points:',[len(t.joint_trajectory.points) for t in result.planned_trajectory])
finally:
    node.destroy_node()
    rclpy.try_shutdown()
