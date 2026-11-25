"""Cartesian demonstration teacher for the fixed Waffle tabletop (metres, radians)."""
import numpy as np


def teacher_action(step, source, goal, tip, joints):
    yaw, shoulder_pitch, elbow_pitch, wrist_pitch, _ = joints
    forearm_pitch = shoulder_pitch + elbow_pitch
    tool_pitch = forearm_pitch + wrist_pitch
    # Use the physical tip and encoder values to locate the shoulder in the world.
    reach = (.024 * np.cos(shoulder_pitch) + .128 * np.sin(shoulder_pitch)
             + .124 * np.cos(forearm_pitch) + .126 * np.cos(tool_pitch))
    height = (-.024 * np.sin(shoulder_pitch) + .128 * np.cos(shoulder_pitch)
              - .124 * np.sin(forearm_pitch) - .126 * np.sin(tool_pitch))
    shoulder = tip - [reach * np.cos(yaw), reach * np.sin(yaw), height]

    def progress(start, duration):
        return np.clip((step - start) / duration, 0., 1.)

    transfer = progress(47, 10)
    pitch = .80 - .12 * transfer
    destination = (1 - transfer) * source[:2] + transfer * goal
    # Approach, lift, lower onto the target, then retreat with open fingers.
    lift = 1 - progress(10, 9) + progress(36, 9) - progress(58, 9) + progress(80, 9)
    target_z = source[2] + .006 + .061 * lift
    grip = -.0095 if 21 <= step < 69 else .012
    offset = destination - shoulder[:2]
    yaw = np.arctan2(offset[1], offset[0])

    # The pad centre lies approximately 12 mm beyond the URDF tip.
    radius = np.linalg.norm(offset) - .138 * np.cos(pitch)
    up = target_z - shoulder[2] + .138 * np.sin(pitch)
    upper_length, forearm_length = np.hypot(.024, .128), .124
    cosine = (radius**2 + up**2 - upper_length**2 - forearm_length**2) / (2 * upper_length * forearm_length)
    elbow = -np.arccos(np.clip(cosine, -1, 1))
    upper = np.arctan2(up, radius) - np.arctan2(
        forearm_length * np.sin(elbow), upper_length + forearm_length * np.cos(elbow))
    shoulder_pitch = np.arctan2(.128, .024) - upper
    elbow_pitch = -upper - elbow - shoulder_pitch
    return np.array([0., 0., yaw, shoulder_pitch, elbow_pitch, pitch - shoulder_pitch - elbow_pitch, grip])
