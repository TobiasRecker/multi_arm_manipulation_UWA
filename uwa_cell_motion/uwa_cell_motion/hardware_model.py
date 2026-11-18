"""Hardware planning model with an opening-independent tool envelope.

Unobserved fingers are not published as measured joints. Collision geometry on
its original link contains the whole opening sweep at the fixed model coordinate
zero. This preserves the existing self-collision exclusions instead of merging
all tool geometry into an allowed rigid component.
"""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from itertools import combinations
import numpy as np
from match_ur_hardware.profiles import load_profiles
from uwa_cell_control.parallel_scan import collision_signature
from uwa_cell_control.scan_separation import Geometry
from uwa_cell_calibration.model import CollisionModel
from uwa_cell_gazebo.configuration import render_description
from .common import all_names,load_layout,default_layout_path,nominal_state,joint_names,sha,BODY_RESERVE_MODEL
from .geometry import SphereModel,box_spheres
from .planning import Problem


def inventory_path():
    # This workspace keeps the inventory alongside the source repository,
    # including relative factory-kinematics paths. Never copy a divergent one.
    for parent in Path(__file__).resolve().parents:
        candidate=parent/'config/hardware_inventory.yaml'
        if candidate.is_file():return candidate
    raise ValueError('Pass --inventory: central hardware inventory not found')


def arm_origins(description,rid):
    from uwa_cell_control.view_geometry import origin
    root=ET.fromstring(description)
    result={}
    for name in joint_names(rid):
        joint=root.find(f"joint[@name='{name}']")
        if joint is None:raise ValueError('Driver joint missing: '+name)
        result[name]=origin(joint.find('origin'))
    return result


def matching_arm(description,expected,rid):
    try:
        actual=arm_origins(description,rid);wanted=arm_origins(expected,rid)
        return all(np.allclose(actual[j],wanted[j],rtol=0,atol=1e-8) for j in wanted)
    except (AttributeError,TypeError,ValueError,KeyError):return False


def opening_envelope(description,names,step=.1):
    """Lipschitz-inflated samples enclose full mesh volumes between samples."""
    root=ET.fromstring(description);geometry=Geometry(description,names)
    zero={j:0. for n in names.values() for j in n};frames0=geometry.fk.frames(zero)
    audit=[]
    for rid,bodies in geometry.bodies.items():
        if len(names[rid])<7:continue
        driver=names[rid][6];joint=root.find(f"joint[@name='{driver}']");limit=joint.find('limit')
        lo,hi=float(limit.get('lower')),float(limit.get('upper'))
        count=max(1,int(np.ceil((hi-lo)/step)));samples=np.linspace(lo,hi,count+1);half=(hi-lo)/(2*count)
        for body in bodies:
            if body.radii[6]<=0:continue
            link=root.find(f"link[@name='{body.link}']")
            original=list(link.findall('collision'))
            # Remove original moving bodies once, before adding sweep spheres.
            if body.index==0:
                for collision in original:link.remove(collision)
                # Unknown fingers must not appear as a measured open pose.
                for visual in list(link.findall('visual')):link.remove(visual)
            centres,radii=box_spheres(body.visual_vertices.min(axis=0),body.visual_vertices.max(axis=0),.05)
            centres=centres@body.fixed[:3,:3].T+body.fixed[:3,3]
            inverse=np.linalg.inv(frames0[body.link]);inflation=float(body.radii[6]*half)
            for value in samples:
                frames=geometry.fk.frames(dict(zero,**{driver:float(value)}))
                relative=inverse@frames[body.link]
                for index,(centre,radius) in enumerate(zip(centres,radii)):
                    point=relative[:3,:3]@centre+relative[:3,3]
                    collision=ET.SubElement(link,'collision',name=f'opening_envelope_{body.index}_{value:.8f}_{index}')
                    ET.SubElement(collision,'origin',xyz=' '.join(map(str,point)))
                    ET.SubElement(ET.SubElement(collision,'geometry'),'sphere',radius=str(float(radius)+inflation))
            audit.append(dict(arm=rid,link=body.link,source_collision=body.index,range_rad=[lo,hi],samples=len(samples),
                between_sample_inflation_m=inflation,method='whole-volume spheres plus analytic joint-motion bound'))
    for element in list(root):
        if element.tag in ('gazebo','ros2_control'):root.remove(element)
    return ET.tostring(root,encoding='unicode'),audit


def model_context(directory,inventory,layout_path=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    layout=load_layout(layout_path or default_layout_path());profiles=load_profiles(inventory)
    if set(profiles)!=set(layout['robots']):raise ValueError('Inventory must contain exactly the four cell arms')
    for rid,p in profiles.items():
        robot=layout['robots'][rid]
        if robot['type']!=p['ur_type']:raise ValueError(rid+': inventory and cell UR types differ')
        if not p['kinematics_file']:raise ValueError(rid+': factory kinematics required')
        # Same central cell anchors/tools, explicit inventory factory kinematics.
        robot['kinematics_file']=p['kinematics_file']
    original,_=render_description(layout,directory)
    description,audit=opening_envelope(original,all_names(layout))
    collision=CollisionModel(description,directory/'moveit')
    # Different opening samples of one mechanical gripper cannot occur at the
    # same time. Their swept hulls overlap internally. Keep all external tool,
    # camera, arm, table and interarm pairs; only the coupled gripper internals
    # are excluded and recorded identically in Python and the native SRDF.
    srdf=ET.fromstring((directory/'moveit/robot.srdf').read_text())
    links=[link.get('name') for link in ET.fromstring(description).findall('link')]
    for rid in profiles:
        for a,b in combinations([n for n in links if n.startswith(rid+'_robotiq_85_')],2):
            collision.scene.allowed_collision_matrix.set_entry(a,b,True)
            ET.SubElement(srdf,'disable_collisions',link1=a,link2=b,reason='CoupledToolOpeningEnvelope')
    (directory/'moveit/robot.srdf').write_text(ET.tostring(srdf,encoding='unicode'))
    return layout,profiles,original,description,collision,audit


class HardwareProblem(Problem):
    def __init__(self,directory,cfg,inventory,layout_path=None):
        self.directory=Path(directory);self.cfg=cfg;self.layout_path=layout_path;self.inventory=str(Path(inventory).resolve())
        self.layout,self.profiles,self.original_description,self.description,self.collision,self.envelope_audit=model_context(directory,inventory,layout_path)
        self.names=all_names(self.layout);self.spheres=SphereModel(self.description,self.names,cfg['sphere_spacing_m'])
        if cfg.get('stopping_reserve_model')==BODY_RESERVE_MODEL:
            self.spheres.enveloped_dofs={r:tuple(range(6,len(n))) for r,n in self.names.items()}
        self.signature=collision_signature(self.description)
        self.binding=sha(json.dumps(dict(inventory=load_profiles(inventory),model=self.signature,config=cfg,
            policy='all-tool-openings-v1'),sort_keys=True))

    def normalize(self,request):
        for rid,names in self.names.items():
            if len(names)>6 and request['start'].get(names[6])!=0.:
                raise ValueError('Unobserved tool model coordinates must be zero; full opening envelope is used')
        for rid,goal in request.get('goals',{}).items():
            if isinstance(goal,dict) and 'target_link' in goal:
                from uwa_cell_gazebo.charuco_views import Chain
                chain=Chain(self.original_description,'world',goal['target_link'])
                # Only rigid TCP/camera frames are meaningful with unknown fingers.
                root=ET.fromstring(self.original_description);parent={j.find('child').get('link'):j for j in root.findall('joint')}
                link=goal['target_link']
                while link!=rid+'_tool0':
                    joint=parent.get(link)
                    if joint is None or joint.get('type')!='fixed':raise ValueError('Hardware Cartesian target must be rigidly attached to tool0')
                    link=joint.find('parent').get('link')
        return super().normalize(request)

    def plan(self,request,method,seed=0,normalized=False):
        result=super().plan(request,method,seed,normalized=normalized)
        result.update(simulation_only=False,hardware_plan=True,hardware_binding=self.binding,inventory=self.inventory,
            tool_policy='all_openings_envelope_no_gripper_command',stop_budget_qualification=(
                'DYNAMIC RESERVE DISABLED BY OPERATOR; GEOMETRIC CHECKS RETAINED'
                if self.cfg.get('stopping_reserve_policy')=='geometric_only' else 'ENGINEERING ASSUMPTIONS - NOT MEASURED ON HARDWARE'))
        return result
