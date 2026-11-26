"""Move the Isaac wheels a short distance and verify both encoder deltas."""
import time
import rclpy
from sensor_msgs.msg import JointState

def advance(distance):
    names = ["wheel_left_joint", "wheel_right_joint"]
    rclpy.init()
    node = rclpy.create_node("lesson13_drive")
    pub = node.create_publisher(JointState, "/isaac/wheel_commands", 1)
    sample = []
    def observe(msg):
        if all(name in msg.name for name in names):
            sample[:] = [msg.position[msg.name.index(name)] for name in names]
    node.create_subscription(JointState,"/isaac/joint_states",observe,1)
    command = JointState(name=names,velocity=[1.0,1.0])
    try:
        end = time.monotonic()+40
        while not sample or not pub.get_subscription_count():
            if time.monotonic()>end:raise TimeoutError("Isaac feedback unavailable")
            rclpy.spin_once(node,timeout_sec=.1)
        start=sample.copy()
        while time.monotonic()<end:
            delta=[(p-q)*.033 for p,q in zip(sample,start)]
            if min(delta)>=distance:
                return {"action":"drive","requested_m":distance,"left_encoder_m":delta[0],"right_encoder_m":delta[1]}
            pub.publish(command)
            rclpy.spin_once(node,timeout_sec=.1)
        raise TimeoutError("Requested wheel travel not reached")
    finally:
        command.velocity=[0.,0.]
        for _ in range(4):
            pub.publish(command)
            rclpy.spin_once(node,timeout_sec=.05)
        node.destroy_node()
        rclpy.shutdown()
