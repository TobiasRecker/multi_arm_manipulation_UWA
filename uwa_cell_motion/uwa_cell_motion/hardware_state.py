"""Explicit hardware/mock boundary and independently advancing device states."""
import json
import os
import socket
import threading
import time
import uuid
from pathlib import Path
import numpy as np
from .common import ROBOT_IDS,sha


def require_domain(mode):
    expected={'hardware':'66','mock':'67'}.get(mode)
    if expected is None or os.environ.get('ROS_DOMAIN_ID')!=expected or os.environ.get('ROS_AUTOMATIC_DISCOVERY_RANGE')!='LOCALHOST':
        raise RuntimeError('Hardware motion requires explicit mode/domain: hardware66 or mock67, LOCALHOST')


def signature(problem,mode):
    return sha(json.dumps(dict(protocol=1,mode=mode,problem=problem.binding),sort_keys=True))


class Peer:
    def __init__(self):self.value=None;self.received=-float('inf')
    def receive(self,value,now,expected,armed):
        try:
            if value['hardware_signature']!=expected or value['armed'] is not armed:return False
            if type(value['sequence']) is not int or not value['instance']:return False
            stamp=float(value['evaluated_monotonic_s'])
            if not np.isfinite(stamp) or not 0<=now-stamp<=.5:return False
            if self.value and value['instance']==self.value['instance'] and value['sequence']<=self.value['sequence']:return False
            self.value=value;self.received=now;return True
        except (KeyError,TypeError,ValueError):return False
    def fresh(self,now,timeout):
        return self.value is not None and 0<=now-self.received<=timeout and 0<=now-self.value['evaluated_monotonic_s']<=timeout


class DeviceStates:
    def __init__(self):self.records={};self.errors={};self.lock=threading.Lock()
    def accept(self,rid,stamp,q,v,now):
        q=np.asarray(q,float);v=np.asarray(v,float)
        if q.shape!=(6,) or v.shape!=(6,) or not np.isfinite(np.r_[q,v,stamp,now]).all():
            self.fail(rid,'Nonfinite/incomplete actual state');return False
        with self.lock:
            previous=self.records.get(rid)
            epoch=previous.get('epoch',0) if previous else 0
            if previous and stamp==previous['device_stamp']:
                self.errors[rid]='DEVICE TIMESTAMP FROZEN'
                return False
            if previous and stamp<previous['device_stamp']:epoch+=1;previous=None
            offset=min(now-stamp,previous['offset']) if previous else now-stamp
            self.records[rid]=dict(q=q.tolist(),v=v.tolist(),device_stamp=stamp,source_stamp=stamp+offset,received=now,offset=offset,epoch=epoch)
            self.errors.pop(rid,None);return True
    def fail(self,rid,error):
        with self.lock:self.errors[rid]=str(error)
    def snapshot(self):
        with self.lock:return dict(self.records),dict(self.errors)


class RtdeStates(DeviceStates):
    """Output-only RTDE. No driver startup, registers, URScript or I/O."""
    def __init__(self,profiles,timeout):
        super().__init__();self.done=threading.Event();self.readers={};self.timeout=timeout
        self.workers=[threading.Thread(target=self.read,args=(r,p['ip']),daemon=True) for r,p in profiles.items()]
        for worker in self.workers:worker.start()
    def read(self,rid,ip):
        from uwa_cell_control.capture_rtde import OutputReader
        while not self.done.is_set():
            reader=None
            try:
                began=time.monotonic();reader=OutputReader(ip)
                if time.monotonic()-began>self.timeout:raise RuntimeError('RTDE subscription handshake exceeds state budget')
                reader.socket.settimeout(self.timeout)
                with self.lock:self.readers[rid]=reader
                # Reconnection does not release any guard/supervisor latch.
                while not self.done.is_set():
                    stamp,q,v=reader.sample()
                    self.accept(rid,stamp,q,v,time.monotonic())
            except Exception as error:self.fail(rid,error)
            finally:
                if reader:reader.close()
                with self.lock:self.readers.pop(rid,None)
            self.done.wait(.5)
    def close(self):
        self.done.set()
        with self.lock:readers=list(self.readers.values())
        for reader in readers:
            try:reader.socket.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        for worker in self.workers:worker.join(timeout=3.)


def dashboard_stop(profile):
    """Only the native STOP verb; never load/play/power/brake/unlock."""
    with socket.create_connection((profile['ip'],profile.get('dashboard_port',29999)),timeout=.25) as stream:
        stream.settimeout(.25)
        def line():
            data=b''
            while not data.endswith(b'\n'):
                part=stream.recv(1)
                if not part:raise RuntimeError('Dashboard connection closed')
                data+=part
                if len(data)>4096:raise RuntimeError('Invalid Dashboard response')
            return data.decode('utf-8',errors='replace').strip()
        line();stream.sendall(b'stop\n');answer=line()
        if answer.lower()!='stopped':raise RuntimeError('Native STOP not confirmed: '+answer)
        return answer


def packet(signature,armed,instance,sequence,**values):
    return dict(hardware_signature=signature,armed=armed,instance=instance,sequence=sequence,
                evaluated_monotonic_s=time.monotonic(),**values)
