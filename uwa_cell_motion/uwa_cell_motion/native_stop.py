"""Small native STOP path independent of ROS initialization/MoveIt/kinematics."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import json
import os
from pathlib import Path
import socket
import time
import yaml


def require_domain(mode):
    expected={'hardware':'66','mock':'67'}.get(mode)
    if expected is None or os.environ.get('ROS_DOMAIN_ID')!=expected or os.environ.get('ROS_AUTOMATIC_DISCOVERY_RANGE')!='LOCALHOST':
        raise RuntimeError('Hardware motion requires explicit mode/domain: hardware66 or mock67, LOCALHOST')


def dashboard_stop(profile):
    deadline=time.monotonic()+.75
    with socket.create_connection((profile['ip'],profile.get('dashboard_port',29999)),timeout=.25) as stream:
        def line():
            data=b''
            while not data.endswith(b'\n'):
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('Native STOP deadline exceeded')
                stream.settimeout(min(.25,remaining));part=stream.recv(1)
                if not part:raise RuntimeError('Dashboard connection closed')
                data+=part
                if len(data)>4096:raise RuntimeError('Invalid Dashboard response')
            return data.decode('utf-8',errors='replace').strip()
        line();stream.sendall(b'stop\n');answer=line()
        if answer.lower()!='stopped':raise RuntimeError('Native STOP not confirmed: '+answer)
        return answer


def stop_all(inventory,mode):
    require_domain(mode);robots=yaml.safe_load(Path(inventory).read_text())['robots'];targets={};result={}
    for rid,profile in robots.items():
        try:
            ipaddress.IPv4Address(profile['ip']);port=profile.get('dashboard_port',29999)
            if type(port) is not int or not 1<=port<=65535:raise ValueError('Invalid Dashboard port')
            targets[rid]=dict(ip=profile['ip'],dashboard_port=port)
        except (KeyError,TypeError,ValueError) as error:result[rid]=dict(acknowledged=False,error=str(error))
    if mode=='mock':return dict(result,**{r:dict(requested=True,mock=True) for r in targets})
    def stop(profile):
        try:return dict(acknowledged=True,response=dashboard_stop(profile))
        except Exception as error:return dict(acknowledged=False,error=str(error))
    with ThreadPoolExecutor(max_workers=4) as executor:result.update(zip(targets,executor.map(stop,targets.values())))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inventory',required=True);parser.add_argument('--mode',choices=['mock','hardware'],default='mock');args=parser.parse_args()
    result=stop_all(args.inventory,args.mode);print(json.dumps(dict(native_stop=result,standstill_confirmed=False)))
    if args.mode=='hardware' and (not result or not all(v.get('acknowledged') for v in result.values())):raise SystemExit(1)
