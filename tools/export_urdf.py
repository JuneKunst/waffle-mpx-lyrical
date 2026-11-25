#!/usr/bin/env python3
"""Expand the simulation URDF and resolve meshes for Isaac's standalone importer."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import xacro
from ament_index_python.packages import get_package_share_directory as share

parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
parser.add_argument('--camera-mount-xyz', default='0.1061547 0 0.065')
parser.add_argument('--camera-mount-rpy', default='0 0 0')
args = parser.parse_args()
model = Path(share('turtlebot3_manipulation_description')) / 'urdf/turtlebot3_manipulation.urdf.xacro'
root = ET.fromstring(xacro.process_file(str(model), mappings={
    'use_sim': 'true', 'camera_mount_xyz': args.camera_mount_xyz,
    'camera_mount_rpy': args.camera_mount_rpy}).toxml())
for control in root.findall('ros2_control'):
    root.remove(control)
for mesh in root.findall('.//mesh'):
    pkg, path = mesh.get('filename').removeprefix('package://').split('/',1)
    file = (Path(share(pkg)) / path).resolve(strict=True)
    mesh.set('filename', str(file))
ET.ElementTree(root).write(args.output, encoding='utf-8', xml_declaration=True)
