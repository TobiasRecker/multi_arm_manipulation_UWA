#!/usr/bin/env python3
"""Freeze hardware carton geometry/contact recipe from the versioned asset.

Pure offline data preparation: no Gazebo, ROS context, drivers or device calls.
Never depend on a previous simulation run's removable collision directory.
"""
import argparse,hashlib,json,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO/'uwa_cell_tasks'))
from uwa_cell_tasks.scene import carton_shapes


def prepare(asset,output,config_path,inventory):
    asset=asset.resolve();output=output.resolve();manifest=json.loads((asset/'asset.json').read_text())
    if manifest['asset_id']!='carton_avocado_v1' or manifest['version']!=1:raise ValueError('This recipe is specific to carton_avocado_v1 version1')
    for name,digest in manifest['files'].items():
        if hashlib.sha256((asset/name).read_bytes()).hexdigest()!=digest:raise ValueError('Asset changed: '+name)
    output.mkdir(parents=True,exist_ok=False);thickness=manifest['quality']['wall_thickness_m']
    shapes=carton_shapes(dict(mesh_file=asset/manifest['visual_mesh'],manifest=manifest),output/'collision',thickness)
    scene=dict(schema_version=1,kind='hardware_static_carton_geometry_only',asset_id=manifest['asset_id'],asset_manifest_sha256=hashlib.sha256((asset/'asset.json').read_bytes()).hexdigest(),asset_directory=str(asset),shapes=shapes,wall_thickness_measured=False,loaded_motion=False,scope='Explicit task geometry proxy, no physics/force qualification')
    (output/'scene.json').write_text(json.dumps(scene,indent=2)+'\n');L,W,_=manifest['dimensions_m'];contacts={}
    for arm,side,x in [('right_front',0,thickness/2),('right_rear',1,L-thickness/2)]:
        top=min(s['wall_base_top_m']for s in shapes if s['axis']==0 and s['side']==side and s['wall_base_top_m'] is not None)
        contacts[arm]=dict(axis=0,side=side,normal_object=[1.,0.,0.],point_object=[x,W/2,top-.0320907634783028],continuous_wall_top_object_m=top)
    seeds={'right_front':[-5.231667152953398,-2.0702897048215143,-1.1545407599672843,-1.4883142141785808,1.5743026531495736,-.5339841813626958],
           'right_rear':[-.6585323329124558,-2.1194263619224905,-1.0841980386102144,-1.509741525602388,1.5710972846863966,.8959402741524013]}
    (output/'contacts.json').write_text(json.dumps(dict(schema_version=1,candidate=dict(contacts=contacts,elbow_signs={'right_front':-1},preferred_ik_seeds=seeds,seed_origin='RF previous successful19November high approach, RR current high pose explicitly accepted by user. Seeds only; solve fresh current target and recheck whole task, never replay.',posture_reason='19November user feedback: RF elbow-down high pose cannot complete this table grasp; retain previously successful elbow branch. Task-specific, not a universal arm posture ban.'),scope='Nominal end-wall recipe; current camera pose and actual open-jaw alignment still required',force_raw=0,speed_raw=16,mass_kg_user_reported=.5,wall_force_reference_n_user_reported=50.,reference_scope='50N per jaw/wall patch, not a measured failure threshold'),indent=2)+'\n')
    from uwa_cell_motion.common import config
    from uwa_cell_motion.hardware_model import HardwareProblem
    model=HardwareProblem(output/'model',config(config_path),inventory)
    (output/'hardware.urdf').write_text(model.original_description)
    print(json.dumps(dict(scene=str(output/'scene.json'),contacts=str(output/'contacts.json'),description=str(output/'hardware.urdf'),model_signature=model.signature,shapes=len(shapes),device_commands=[]),indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--asset',type=Path,default=REPO/'uwa_cell_description/assets/carton_avocado_v1');ap.add_argument('--output',type=Path,required=True);ap.add_argument('--config',type=Path,default=REPO/'uwa_cell_motion/config/hardware_carton_supported.yaml');ap.add_argument('--inventory',type=Path,default=REPO/'config/hardware_inventory.yaml');a=ap.parse_args();prepare(a.asset,a.output,a.config,a.inventory)
