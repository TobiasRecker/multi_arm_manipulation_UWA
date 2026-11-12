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
    from uwa_cell_description.configuration import default_layout_path
    return default_layout_path()


def load_inputs(inventory,layout,arms):
    profiles=load_profiles(inventory)
    from uwa_cell_description.configuration import load_layout
    data=load_layout(layout)
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
    measured=layout.get('calibration',{}).get('robots',{}).get(rid,{})
    if measured.get('kinematics_file'):
        if profile['kinematics_file'] and Path(profile['kinematics_file']).read_bytes()!=Path(measured['kinematics_file']).read_bytes():
            raise ValueError(f'{rid}: inventory and measured calibration have different kinematics')
        args['kinematics_params']=measured['kinematics_file']
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
    # Display measured optical and board frames without relocating provisional bases.
    if 'fit' in measured:
        from uwa_cell_description.calibration_profile import origin, rigid
        for suffix,parent,matrix in [
                ('wrist_camera_optical_frame',prefix+'tool0',measured['fit']['T_tool0_camera']),
                ('measured_board_frame',prefix+'base_link',measured['fit']['T_base_board'])]:
            ET.SubElement(robot,'link',name=prefix+suffix)
            joint=ET.SubElement(robot,'joint',name=prefix+suffix+'_joint',type='fixed')
            ET.SubElement(joint,'parent',link=parent);ET.SubElement(joint,'child',link=prefix+suffix)
            origin(joint,rigid(matrix))
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
