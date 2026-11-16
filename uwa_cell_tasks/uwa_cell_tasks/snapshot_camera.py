"""Static Gazebo photo world, physically separate from the contact simulator.

Simulator truth defines the rendered scene as it does in any simulator. It is
never supplied as a pose prior to the image estimator. Snapshot timestamps and
the physical-state timestamp are different, explicit clock domains.
"""
from collections import deque
from functools import partial
import json
import os
from pathlib import Path
import signal
import subprocess
from threading import Lock
import time
import uuid
import xml.etree.ElementTree as ET
from copy import deepcopy

import numpy as np
from scipy.spatial.transform import Rotation
import rclpy
from uwa_cell_motion.node import MotionNode
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from std_srvs.srv import Trigger
from gz.transport import Node as TransportNode
from gz.msgs.image_pb2 import Image,RGB_INT8
from gz.msgs.camera_info_pb2 import CameraInfo
from .core import CAMERAS
from uwa_cell_gazebo.charuco_views import Chain


def frozen_robot(description,positions,topic_prefix):
    root=ET.fromstring(description)
    for element in list(root):
        if element.tag=='ros2_control' or element.tag=='gazebo' and element.get('reference') is None:root.remove(element)
    for joint in root.findall('joint'):
        if joint.get('type') not in ('revolute','continuous'):continue
        origin=joint.find('origin')
        if origin is None:origin=ET.SubElement(joint,'origin')
        rpy=np.fromstring(origin.get('rpy','0 0 0'),sep=' ')
        axis=np.fromstring(joint.find('axis').get('xyz'),sep=' ')
        rotation=Rotation.from_euler('xyz',rpy)*Rotation.from_rotvec(axis*positions[joint.get('name')])
        origin.set('rpy',' '.join(map(str,rotation.as_euler('xyz'))));joint.set('type','fixed')
        for tag in ('axis','limit','mimic','dynamics'):
            for child in list(joint.findall(tag)):joint.remove(child)
    for link in root.findall('link'):
        for tag in ('collision','inertial'):
            for child in list(link.findall(tag)):link.remove(child)
    for element in root.findall('gazebo'):
        if element.get('reference','').startswith(('left_front_','left_rear_')):
            for sensor in list(element.findall('sensor')):element.remove(sensor)
    ET.SubElement(ET.SubElement(root,'gazebo'),'static').text='true'
    text=ET.tostring(root,encoding='unicode').replace('/uwa_cell/',topic_prefix+'/')
    return text


def static_visual_model(description,positions,topic_prefix):
    """Direct SDF visuals avoid URDF fixed-joint reduction/dangling frames."""
    frozen=frozen_robot(description,positions,topic_prefix);root=ET.fromstring(frozen)
    model=ET.Element('model',name='snapshot_robot');ET.SubElement(model,'static').text='true'
    materials={m.get('name'):m for m in root.findall('material')}
    for source in root.findall('link'):
        name=source.get('name');sensors=root.findall(f"gazebo[@reference='{name}']/sensor")
        if not source.findall('visual') and not sensors:continue
        link=ET.SubElement(model,'link',name=name)
        t=Chain(frozen,'world',name).forward({})
        ET.SubElement(link,'pose').text=' '.join(map(str,[*t[:3,3],*Rotation.from_matrix(t[:3,:3]).as_euler('xyz')]))
        for index,visual in enumerate(source.findall('visual')):
            out=ET.SubElement(link,'visual',name=name+'_visual_'+str(index))
            origin=visual.find('origin')
            if origin is not None:ET.SubElement(out,'pose').text=origin.get('xyz','0 0 0')+' '+origin.get('rpy','0 0 0')
            geometry=ET.SubElement(out,'geometry');shape=list(visual.find('geometry'))[0]
            target=ET.SubElement(geometry,shape.tag)
            if shape.tag=='mesh':
                ET.SubElement(target,'uri').text=shape.get('filename')
                ET.SubElement(target,'scale').text=shape.get('scale','1 1 1')
            else:
                for key,value in shape.attrib.items():ET.SubElement(target,key).text=value
            material=visual.find('material')
            if material is not None:
                color=material.find('color')
                if color is None and material.get('name') in materials:color=materials[material.get('name')].find('color')
                if color is not None:
                    mat=ET.SubElement(out,'material')
                    ET.SubElement(mat,'ambient').text=color.get('rgba');ET.SubElement(mat,'diffuse').text=color.get('rgba')
        for sensor in sensors:link.append(deepcopy(sensor))
    return model


class SnapshotCamera(MotionNode):
    def __init__(self,namespace,directory):
        super().__init__('task_snapshot_camera',namespace=namespace)
        self.ns=namespace;self.directory=Path(directory);self.lock=Lock();self.transport=TransportNode()
        self.q={};self.q_stamp=0.;self.truth=None;self.received=0.;self.frames={};self.infos={};self.topics=[];self.process=None
        self.create_subscription(JointState,namespace+'/joint_states',self.joints,qos_profile_sensor_data)
        self.create_subscription(String,namespace+'/tasks/object_truth',self.object_message,qos_profile_sensor_data)
        self.create_service(Trigger,'tasks/camera_capture',self.capture)

    def joints(self,msg):
        self.q=dict(zip(msg.name,msg.position));self.q_stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9;self.received=time.monotonic()
    def object_message(self,msg):self.truth=json.loads(msg.data)

    def info(self,camera,msg):
        with self.lock:self.infos[camera]=msg

    def image(self,camera,msg):
        with self.lock:
            if camera not in self.infos or msg.pixel_format_type!=RGB_INT8:return
            info=self.infos[camera];stamp=msg.header.stamp.sec+msg.header.stamp.nsec/1e9
            if self.frames[camera] and stamp<=self.frames[camera][-1]['stamp']:return
            if (msg.width,msg.height)!=(info.width,info.height):return
            pixels=np.frombuffer(msg.data,np.uint8).reshape(msg.height,msg.step)[:,:msg.width*3].reshape(msg.height,msg.width,3)
            self.frames[camera].append(dict(arm=camera,stamp=stamp,K=list(info.intrinsics.k),D=list(info.distortion.k),pixels=pixels,
                environment='own_gazebo_snapshot_renderer'))

    def capture(self,request,response):
        if not self.q or not self.truth or time.monotonic()-self.received>.2:
            response.success=False;response.message='WAITING for fresh physical simulation state';return response
        positions=dict(self.q);truth=dict(self.truth);physical_stamp=self.q_stamp
        directory=self.directory/'captures'/uuid.uuid4().hex;directory.mkdir(parents=True)
        token='photo_'+directory.name;prefix=self.ns+'/'+token;world_name='uwa_'+token
        try:
            robot=static_visual_model((self.directory/'robot.urdf').read_text(),positions,prefix)
            root=ET.parse(self.directory/'world.sdf').getroot();world=root.find('world');world.set('name',world_name)
            for model in list(world.findall('model')):
                if model.get('name')!='uwa_grasp_oak':world.remove(model)
            for plugin in list(world.findall('plugin')):
                if plugin.get('filename') not in ('gz-sim-scene-broadcaster-system',):world.remove(plugin)
            sensors=ET.SubElement(world,'plugin',filename='gz-sim-sensors-system',name='gz::sim::systems::Sensors')
            ET.SubElement(sensors,'render_engine').text='ogre2';world.append(robot)
            carton=ET.parse(self.directory/'carton.sdf').getroot().find('model');carton.set('name','snapshot_carton')
            carton.find('static').text='true'
            t=np.array(truth['T_world_object']);carton.find('pose').text=' '.join(map(str,[*t[:3,3],*Rotation.from_matrix(t[:3,:3]).as_euler('xyz')]))
            for link in carton.findall('link'):
                for child in list(link):
                    if child.tag!='visual':link.remove(child)
            for plugin in list(carton.findall('plugin')):carton.remove(plugin)
            world.append(carton)
            content=ET.tostring(root,encoding='unicode').replace('/uwa_cell/',prefix+'/')
            path=directory/'photos.sdf';path.write_text(content)
            self.frames={c:deque(maxlen=3) for c in CAMERAS};self.infos={}
            for camera in CAMERAS:
                base=prefix+('/oak_overview/rgb/' if camera=='oak' else '/'+camera+'/wrist_camera/')
                for suffix,kind,callback in [('image_raw',Image,self.image),('camera_info',CameraInfo,self.info)]:
                    topic=base+suffix
                    if not self.transport.subscribe(kind,topic,partial(callback,camera)):raise RuntimeError('Snapshot subscription failed')
                    self.topics.append(topic)
            with (directory/'renderer.log').open('w') as log:
                # Photo rendering is best-effort background work. Keep Ogre/
                # Mesa worker bursts off most CPUs used by physics/watchdogs;
                # their existing freshness deadlines remain unchanged.
                available=sorted(os.sched_getaffinity(0))
                render_cpus=available[-max(1,len(available)//4):]
                render_env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',LP_NUM_THREADS='2')
                render_policy=dict(cpus=render_cpus,nice=10,worker_threads=2)
                self.process=subprocess.Popen(['nice','-n','10','taskset','-c',','.join(map(str,render_cpus)),
                    'gz','sim','-s','-r',str(path),'--headless-rendering','-v','2'],env=render_env,
                    stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                end=time.monotonic()+25.;snapshot=None
                while time.monotonic()<end:
                    if self.process.poll() is not None:raise RuntimeError('Snapshot renderer exited; inspect '+str(directory/'renderer.log'))
                    with self.lock:
                        if all(len(frames)==3 for frames in self.frames.values()):
                            snapshot=[dict(frame) for frames in self.frames.values() for frame in frames];break
                    time.sleep(.02)
                if snapshot is None:raise TimeoutError('Snapshot renderer did not deliver every camera')
                records=[]
                for index,frame in enumerate(snapshot):
                    image_path=directory/f'{frame["arm"]}-{index}.npy';np.save(image_path,frame.pop('pixels')[:,:,::-1])
                    records.append(dict(frame,image=str(image_path),snapshot_physics_stamp=physical_stamp,
                        snapshot_physics_joint_positions=positions,clock_domain=world_name,renderer_cpu_policy=render_policy))
                response.success=True;response.message=json.dumps(records)
        except Exception as error:
            response.success=False;response.message=str(error)
        finally:self.stop_renderer()
        return response

    def stop_renderer(self):
        if self.process and self.process.poll() is None:
            os.killpg(self.process.pid,signal.SIGINT)
            try:self.process.wait(timeout=5.)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid,signal.SIGTERM);self.process.wait(timeout=5.)
        self.process=None
        for topic in self.topics:self.transport.unsubscribe(topic)
        self.topics=[]

    def close(self):self.stop_renderer()
