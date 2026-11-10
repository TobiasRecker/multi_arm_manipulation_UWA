"""Live profile/TF/rollback test. Requires an idle cell with a completed full session.

Does not command robot motion. Leaves the supplied valid profile active.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading
import time

import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy
from rclpy.time import Time
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from tf2_ros import Buffer,TransformListener,TransformException
from uwa_cell_calibration.client import Client
from uwa_cell_calibration_msgs.srv import ApplyCalibration
from uwa_cell_calibration.storage import atomic_json,fingerprint
from uwa_cell_gazebo.charuco import pose_error,table_board_transform
from uwa_cell_gazebo.charuco_check import tf_matrix
from uwa_cell_gazebo.charuco_views import Chain
from uwa_cell_gazebo.configuration import ROBOT_IDS,joint_names


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    rclpy.init();node=Client();executor=SingleThreadedExecutor();executor.add_node(node)
    buffer=Buffer();listener=TransformListener(buffer,node)
    descriptions={};positions={}
    qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
    for name,topic in [('raw','/uwa_cell/robot_description'),('calibrated','/uwa_cell/calibrated/robot_description')]:
        node.create_subscription(String,topic,lambda m,n=name:descriptions.update({n:m.data}),qos)
    node.create_subscription(JointState,'/uwa_cell/joint_states',lambda m:positions.update(zip(m.name,m.position)),10)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
    def until(condition,seconds=20):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            node.pulse()
            if condition():return
            time.sleep(.03)
        raise TimeoutError(str(node.state)+' '+node.error)
    try:
        until(lambda:len(descriptions)==2 and bool(positions) and node.state.get('active_profile'))
        assert node.state['phase'] in ('IDLE','COMPLETE','READY','STOPPED','ERROR')
        result=json.loads((args.session/'result.json').read_text())
        plan=json.loads((args.session/'plan.json').read_text());layout=plan['layout']
        active=args.session.parent/'profiles/active.json'
        before=active.read_bytes();raw=descriptions['raw'];calibrated=descriptions['calibrated']
        assert fingerprint(raw)==result['description_fingerprint']
        assert 'calibrated/' not in raw and 'calibrated/left_front_base_link' in calibrated
        report={'raw_description_unchanged':True,'separate_tf_trees':True,'tf_errors':{}}
        report['return_error_rad']=max(abs(positions[j]-plan['start'][j]) for rid in ROBOT_IDS for j in joint_names(rid))
        assert report['return_error_rad']<.02
        def lookup(a,b):
            until(lambda:buffer.can_transform(a,b,Time()))
            return tf_matrix(buffer.lookup_transform(a,b,Time()))
        for rid in ROBOT_IDS:
            table=layout['robots'][rid]['table']
            nominal=Chain(raw,'world',rid+'_base_link').forward(positions)
            assert pose_error(lookup('world',rid+'_base_link'),nominal)['translation_m']<1e-6
            x=np.asarray(result['robots'][rid]['T_tool0_camera'])
            estimated=lookup('calibrated/'+rid+'_tool0','calibrated/'+rid+'_wrist_camera_optical_frame')
            assert pose_error(estimated,x)['translation_m']<1e-6
            expected=table_board_transform(layout['charuco'],table)@np.linalg.inv(result['robots'][rid]['T_base_board'])
            error=pose_error(lookup('calibrated/'+table+'_table_top','calibrated/'+rid+'_base_link'),expected)
            assert error['translation_m']<1e-6 and error['rotation_deg']<1e-4
            report['tf_errors'][rid]=error
        testdir=args.session/'profile_checks';testdir.mkdir(exist_ok=True)
        def apply(path):
            node.error=''
            until(node.apply_client.service_is_ready)
            future=node.service(node.apply_client,ApplyCalibration.Request(result_path=str(path.resolve()),client_id=node.client_id))
            assert future is not None
            until(future.done)
            return future.result()
        bad=deepcopy(result);bad['robots']['left_front']['validation']['median_reprojection_rms_px']=10
        invalid=testdir/'invalid_quality.json';atomic_json(invalid,bad)
        assert not apply(invalid).accepted
        assert active.read_bytes()==before and descriptions['calibrated']==calibrated
        report['invalid_quality_preserved_previous_profile']=True
        # Force the right-front arm onto the left-front mounting position in
        # the candidate planning model. Physical Gazebo mounts are untouched.
        bad=deepcopy(result)
        world_table=Chain(raw,'world','right_table_top').forward({})
        world_base=Chain(raw,'world','left_front_base_link').forward({})
        desired=np.linalg.inv(world_table)@world_base
        bad['robots']['right_front']['T_base_board']=(np.linalg.inv(desired)@table_board_transform(layout['charuco'],'right')).tolist()
        collision=testdir/'colliding_model.json';atomic_json(collision,bad)
        assert apply(collision).accepted
        until(lambda:node.state.get('phase')=='ERROR' and 'collision' in node.state.get('message',''))
        assert active.read_bytes()==before and descriptions['calibrated']==calibrated
        report['colliding_model_preserved_previous_profile']=True
        old=node.state['active_profile']
        assert apply(args.session/'result.json').accepted
        until(lambda:node.state.get('phase')=='COMPLETE' and node.state.get('active_profile')!=old)
        assert descriptions['raw']==raw
        assert json.loads(active.read_text())['robots']==result['robots']
        report['valid_profile_reactivated']=True
        report['active_profile']=node.state['active_profile']
        report['active_sha256']=hashlib.sha256(active.read_bytes()).hexdigest()
        atomic_json(args.output,report);print(json.dumps(report,indent=2))
    finally:
        executor.shutdown(timeout_sec=2);thread.join(timeout=2);node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
