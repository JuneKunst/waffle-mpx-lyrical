"""List installed Waffle GPU packages, composable nodes, launch files and examples."""
import argparse
from pathlib import Path
from ament_index_python.packages import get_packages_with_prefixes
from ament_index_python.resources import get_resource

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('filter',nargs='?',default='')
args=p.parse_args()
prefixes=get_packages_with_prefixes()
packages={line.replace('-','_') for line in Path(__file__).with_name('packages.txt').read_text().splitlines()
          if line and not line.startswith('#')}
packages.update(n for n in prefixes if n.startswith(('isaac_ros_','nvblox','isaac_mapping')))
try:
    from isaac_ros_examples import LAUNCH_FRAGMENT_SPECS
except ImportError:
    LAUNCH_FRAGMENT_SPECS={}
for name in sorted(n for n in packages if args.filter in n):
    if name not in prefixes:
        print(name,'[install on GPU host]')
        continue
    print(name)
    root=Path(prefixes[name])/'share'/name
    launch=root/'launch'
    for file in sorted(launch.glob('*')) if launch.is_dir() else []:
        if file.suffix in ['.xml','.yaml'] or (file.suffix=='.py' and 'def generate_launch_description(' in file.read_text()):
            print('  launch:',file.name)
    for key,spec in LAUNCH_FRAGMENT_SPECS.items():
        if spec.package==name: print('  fragment:',key)
    try: plugins,_=get_resource('rclcpp_components',name)
    except LookupError: continue
    for line in plugins.splitlines(): print('  component:',line.split(';')[0])
