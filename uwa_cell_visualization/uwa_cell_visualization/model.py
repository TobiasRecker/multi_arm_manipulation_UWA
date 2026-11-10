"""Official UR kinematics with unique display frames and provisional cell mounts."""
from copy import deepcopy
import math
from pathlib import Path
from xml.etree import ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import xacro
import yaml
from match_ur_hardware.profiles import JOINTS,load_profiles

ARMS=('right_front','right_rear')
COLOURS={'right_front':(1.,.68,.04),'right_rear':(.03,1.,.85)}
EMPTY_MODEL='<robot name="no_current_hardware_data"><link name="world"/></robot>'


def paths():
    return Path(get_package_share_directory('uwa_cell_description'))/'config/cell_layout.yaml'


def load_inputs(inventory,layout,arms):
    profiles=load_profiles(inventory)
    data=yaml.safe_load(Path(layout).expanduser().read_text())
    if not arms or len(arms)!=len(set(arms)) or not set(arms)<=set(ARMS):
        raise ValueError('Measured overlay supports unique right_front/right_rear arm IDs')
    for rid in arms:
        if rid not in data['robots']:raise ValueError(f'{rid}: missing cell mount')
    return profiles,data


def vector(values):
    if len(values)!=3 or not all(math.isfinite(float(x)) for x in values):
        raise ValueError('Expected three finite coordinates')
    return ' '.join(str(float(x)) for x in values)


def description(profile,layout,offset=(0.,0.,0.)):
    rid=profile['id'];prefix='real_'+rid+'_'
    share=Path(get_package_share_directory('ur_description'));kind=profile['ur_type']
    args={'name':'real_'+rid,'ur_type':kind,'tf_prefix':prefix,'force_abs_paths':'true'}
    if profile['kinematics_file']:args['kinematics_params']=profile['kinematics_file']
    robot=ET.fromstring(xacro.process_file(str(share/'urdf/ur.urdf.xacro'),mappings=args).toxml())
    mount=layout['robots'][rid];table=layout['tables'][mount['table']]
    table_frame=prefix+'mount_table';top_frame=prefix+'mount_top'
    for name in [table_frame,top_frame]:ET.SubElement(robot,'link',name=name)
    def fixed(name,parent,child,xyz,rpy):
        joint=ET.SubElement(robot,'joint',name=name,type='fixed')
        ET.SubElement(joint,'parent',link=parent);ET.SubElement(joint,'child',link=child)
        ET.SubElement(joint,'origin',xyz=vector(xyz),rpy=vector(rpy))
    fixed(prefix+'table_pose','world',table_frame,[a+b for a,b in zip(table['xyz'],offset)],table['rpy'])
    fixed(prefix+'table_height',table_frame,top_frame,[0,0,table['height']],[0,0,0])
    base=robot.find(f"joint[@name='{prefix}base_joint']")
    base.find('parent').set('link',top_frame)
    base.find('origin').set('xyz',vector(mount['mount_xyz']))
    base.find('origin').set('rpy',vector(mount['mount_rpy']))
    # Official STL shell meshes have no embedded colours, so measured arms are
    # unambiguously gold/cyan. Kinematics are the unmodified official UR chain.
    for link in robot.findall('link'):
        collisions=link.findall('collision')
        for old in link.findall('visual'):link.remove(old)
        for collision in collisions:
            visual=ET.SubElement(link,'visual')
            for child in collision:
                if child.tag in ('origin','geometry'):visual.append(deepcopy(child))
            material=ET.SubElement(visual,'material',name=prefix+'measured_colour')
            ET.SubElement(material,'color',rgba=' '.join(map(str,(*COLOURS[rid],1.))))
        for tag in ('collision','inertial'):
            for old in link.findall(tag):link.remove(old)
    return ET.tostring(robot,encoding='unicode')


def map_positions(names,positions,profile):
    if len(names)!=len(positions) or len(names)!=len(set(names)):
        raise ValueError('Malformed or duplicate JointState names')
    source=dict(zip(names,positions))
    values=[float(source[profile['prefix']+joint]) for joint in JOINTS]
    if not all(math.isfinite(value) for value in values):raise ValueError('Non-finite joint position')
    return values
