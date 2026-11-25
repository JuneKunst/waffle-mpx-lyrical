"""Generate cuMotion/cuRobo inputs for a stationary base and fixed gripper aperture."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml
import numpy as np
from scipy.spatial.transform import Rotation

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('urdf',type=Path)
parser.add_argument('out',type=Path)
parser.add_argument('--aperture-joint',type=float,default=.01)
args=parser.parse_args()
if not -.01<=args.aperture_joint<=.019:
    parser.error('gripper joint must be within [-.010, .019] m')
root=ET.parse(args.urdf)
active=[f'joint{i}' for i in range(1,5)]
for joint in root.findall('joint'):
    if joint.get('type')=='fixed' or joint.get('name') in active:
        continue
    if joint.get('type')=='prismatic':
        origin=joint.find('origin')
        axis=np.fromstring(joint.find('axis').get('xyz'),sep=' ')
        xyz=np.fromstring(origin.get('xyz'),sep=' ')+axis*args.aperture_joint
        origin.set('xyz',' '.join(map(str,xyz)))
    joint.set('type','fixed')
    for tag in ['axis','limit','mimic','dynamics']:
        item=joint.find(tag)
        if item is not None:
            joint.remove(item)
args.out.mkdir(parents=True,exist_ok=True)
root.write(args.out/'arm.urdf',encoding='utf-8',xml_declaration=True)

# Voxelize triangle surfaces. Every sampled cell is bounded by its circumsphere;
# half a sample spacing is added to cover the gaps between surface samples.
spheres={}
for link in root.findall('link'):
    name=link.get('name')
    cells=set()
    exact=[]
    size={'base_link':.035, 'base_scan':.0075, 'link3':.011}.get(name,.022)
    for shape in link.findall('collision'):
        geom=shape.find('geometry')[0]
        if geom.tag=='box' and name=='base_scan':
            dimensions=np.fromstring(geom.get('size'),sep=' ')
            divisions=np.ceil(dimensions/.011).astype(int)
            step=dimensions/divisions
            for cell in np.ndindex(tuple(divisions)):
                center=(np.array(cell)+.5)*step-dimensions/2
                exact.append(dict(center=center.tolist(),radius=float(np.linalg.norm(step)/2)))
            continue
        if geom.tag=='mesh':
            tri=np.fromfile(geom.get('filename'),offset=84,
                dtype=[('n','<f4',3),('v','<f4',(3,3)),('a','<u2')])['v']*np.fromstring(geom.get('scale','1 1 1'),sep=' ')
        elif geom.tag=='box':
            from scipy.spatial import ConvexHull
            points=(np.indices((2,2,2)).reshape(3,-1).T-.5)*np.fromstring(geom.get('size'),sep=' ')
            tri=points[ConvexHull(points).simplices]
        elif geom.tag in ('sphere','cylinder'):
            radius=float(geom.get('radius'))
            height=float(geom.get('length',2*radius))
            from scipy.spatial import ConvexHull
            points=(np.indices((2,2,2)).reshape(3,-1).T-.5)*[2*radius,2*radius,height]
            tri=points[ConvexHull(points).simplices]
        else:
            raise ValueError(geom.tag)
        origin=shape.find('origin')
        if origin is not None:
            rot=Rotation.from_euler('xyz',np.fromstring(origin.get('rpy','0 0 0'),sep=' ')).as_matrix()
            tri=tri@rot.T+np.fromstring(origin.get('xyz','0 0 0'),sep=' ')
        levels=np.maximum(1,np.ceil(np.linalg.norm(tri-np.roll(tri,1,axis=1),axis=2).max(1)/(size/2))).astype(int)
        for count in np.unique(levels):
            faces=tri[levels==count]
            for i in range(count+1):
                for j in range(count+1-i):
                    points=faces[:,0]+(faces[:,1]-faces[:,0])*i/count+(faces[:,2]-faces[:,0])*j/count
                    cells.update(map(tuple,np.unique(np.floor(points/size).astype(int),axis=0)))
    if cells or exact:
        spheres[name]=exact+[{'center':((np.array(cell)+.5)*size).round(6).tolist(),'radius':round(size*1.37,6)} for cell in sorted(cells)]
# Adjacent joint assemblies and pairs rigidly fixed to the same body may touch.
links={j.find('child').get('link'):j for j in root.findall('joint')}
def rigid_group(name):
    while name in links and links[name].get('type')=='fixed':
        name=links[name].find('parent').get('link')
    return name
ignore={}
srdf=next((Path(__file__).resolve().parents[1]/'turtlebot3_manipulation_moveit_config/config').glob('*.srdf'))
pairs={frozenset((el.get('link1'),el.get('link2'))) for el in ET.parse(srdf).findall('disable_collisions')}
for i,a in enumerate(spheres):
    excluded=[b for b in list(spheres)[i+1:] if rigid_group(a)==rigid_group(b) or frozenset((a,b)) in pairs]
    if excluded: ignore[a]=excluded
xrdf=dict(format='xrdf',format_version=1.0,modifiers=[dict(set_base_frame='base_footprint')],
          default_joint_positions=dict.fromkeys(active,0.),cspace=dict(joint_names=active,
          acceleration_limits=[1.]*4,jerk_limits=[8.]*4),tool_frames=['end_effector_link'],
          collision=dict(geometry='waffle'),self_collision=dict(geometry='waffle',ignore=ignore),
          geometry=dict(waffle=dict(spheres=spheres)))
(args.out/'arm.xrdf').write_text(yaml.safe_dump(xrdf,sort_keys=False))
print({name:len(s) for name,s in spheres.items()})
