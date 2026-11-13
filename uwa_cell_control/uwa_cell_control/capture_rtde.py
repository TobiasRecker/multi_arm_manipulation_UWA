"""Output-only RTDE stationarity audit, independent of hardware ROS drivers.

No input recipes, registers, scripts, I/O, controller or robot-program commands.
The only outbound packets negotiate/subscribe/start DATA OUTPUT streaming.
"""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import socket
import struct
import threading
import time

import yaml
from .capture_telemetry import StationarityAudit


class OutputReader:
    def __init__(self,host):
        self.socket=socket.create_connection((host,30004),timeout=2)
        self.socket.settimeout(.4)
        try:
            if self.request(86,struct.pack('>H',2))!=b'\x01':raise RuntimeError('RTDE protocol2 rejected')
            recipe=self.request(79,struct.pack('>d',20.)+b'timestamp,actual_q,actual_qd')
            if len(recipe)<2 or recipe[0]==0 or recipe[1:]!=b'DOUBLE,VECTOR6D,VECTOR6D':
                raise RuntimeError('Unexpected output-only RTDE recipe')
            self.recipe=recipe[0]
            if self.request(83)!=b'\x01':raise RuntimeError('RTDE output subscription rejected')
        except BaseException:self.socket.close();raise

    def exact(self,count):
        parts=[]
        while count:
            part=self.socket.recv(count)
            if not part:raise RuntimeError('RTDE output connection ended')
            parts.append(part);count-=len(part)
        return b''.join(parts)

    def receive(self):
        size,kind=struct.unpack('>HB',self.exact(3))
        if not 3<=size<=4096:raise RuntimeError('Invalid RTDE packet length')
        return kind,self.exact(size-3)

    def request(self,kind,payload=b''):
        if kind not in (86,79,83):raise ValueError('Only output-stream setup is supported')
        self.socket.sendall(struct.pack('>HB',len(payload)+3,kind)+payload)
        while True:
            received,data=self.receive()
            if received==kind:return data

    def sample(self):
        while True:
            kind,data=self.receive()
            if kind!=85:continue
            if len(data)!=105 or data[0]!=self.recipe:raise RuntimeError('Invalid RTDE output data')
            values=struct.unpack('>13d',data[1:])
            if not math.isfinite(values[0]) or values[0]<0:raise RuntimeError('Invalid controller timestamp')
            return values[0],list(values[1:7]),list(values[7:13])

    def close(self):self.socket.close()


class RtdeCaptureMonitor:
    def __init__(self,workspace,directory,arms):
        from match_ur_hardware.profiles import load_profiles
        path=Path(workspace)/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml'
        profiles=load_profiles(path);inventory=yaml.safe_load(path.read_text())['robots']
        self.audit=StationarityAudit({rid:profiles[rid]['joint_names'] for rid in arms})
        self.log=(Path(directory)/'joint_samples.jsonl').open('w');self.directory=Path(directory)
        self.stopped=threading.Event();self.log_lock=threading.Lock();self.readers=[]
        def read(rid):
            reader=None;previous=None
            try:
                reader=OutputReader(inventory[rid]['ip']);self.readers.append(reader)
                while not self.stopped.is_set():
                    stamp,q,qd=reader.sample();now=time.monotonic()
                    if previous is not None and stamp<=previous:raise RuntimeError('Controller timestamp did not advance')
                    previous=stamp
                    if self.audit.receive(rid,q,qd,now):
                        record=dict(arm=rid,joint_names=self.audit.names[rid],positions=q,velocities=qd,
                            received_monotonic=now,controller_timestamp_s=stamp,
                            recorded_at=datetime.now(timezone.utc).isoformat(),source='output-only RTDE30004')
                        with self.log_lock:self.log.write(json.dumps(record,allow_nan=False)+'\n')
            except Exception as error:
                if not self.stopped.is_set():
                    with self.audit.lock:self.audit.violations.add(rid+': RTDE observer failed: '+str(error))
            finally:
                if reader:reader.close()
        self.workers=[threading.Thread(target=read,args=(rid,),daemon=True) for rid in arms]
        for worker in self.workers:worker.start()
        def watch():
            while not self.stopped.wait(.025):self.audit.check_freshness(time.monotonic())
        self.thread=threading.Thread(target=watch,daemon=True);self.thread.start()

    def wait_still(self,timeout=5.):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if self.audit.violations:raise RuntimeError('; '.join(sorted(self.audit.violations)))
            if self.audit.ready(time.monotonic()):self.audit.arm(time.monotonic());return
            time.sleep(.025)
        raise RuntimeError('Fresh stationary RTDE output unavailable for all selected arms')

    def finish(self):
        self.audit.check_freshness(time.monotonic());self.stopped.set();self.thread.join(timeout=1)
        for worker in self.workers:worker.join(timeout=3)
        if any(w.is_alive() for w in self.workers):
            with self.audit.lock:self.audit.violations.add('RTDE observer did not finish')
        self.log.close();report=self.audit.summary()
        report.update(joint_samples='joint_samples.jsonl',telemetry_source='output-only RTDE30004',
            timestamp_kind='controller output timestamp plus host monotonic receipt; not exposure synchronization')
        (self.directory/'stationarity.json').write_text(json.dumps(report,indent=2)+'\n');return report
