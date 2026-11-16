#!/usr/bin/env python3
"""Apply this workstation's measured CPU profile to one own simulation launch.

Run after all launch nodes are ready, before starting a recipe. Other launches,
renderers, cameras and hardware processes are never changed. This reserves no
CPUs from other applications and provides no real-time scheduling guarantee.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from uwa_cell_motion.common import simulation_only
from uwa_cell_tasks.core import seal,write_json
from uwa_cell_tasks.scene import verify_scene


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',type=Path,required=True)
    args=parser.parse_args();simulation_only();scene=verify_scene(args.scene)
    directory=args.scene.resolve();processes={}
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            argv=(path/'cmdline').read_bytes().decode().rstrip('\0').split('\0')
            status=(path/'status').read_text().splitlines()
            parent=int(next(s for s in status if s.startswith('PPid:')).split()[1])
        except (OSError,UnicodeError,StopIteration):continue
        processes[int(path.name)]=(argv,parent)
    launches=[pid for pid,(a,_) in processes.items() if len(a)>5 and Path(a[1]).name=='ros2'
        and a[2:5]==['launch','uwa_cell_tasks','grasp.launch.py'] and 'scene:='+str(directory) in a]
    if len(launches)!=1:raise RuntimeError('Exactly one matching own simulation launch required')
    def descendant(pid):
        seen=set()
        while pid in processes and pid not in seen:
            if pid==launches[0]:return True
            seen.add(pid);pid=processes[pid][1]
        return False
    selected={}
    for pid,(a,_) in processes.items():
        if not descendant(pid):continue
        role=None
        if str(directory/'world.live.sdf') in a:role='physics'
        if len(a)>3 and Path(a[1]).name=='cell_task' and a[2] in ('guard','supervisor'):role=a[2]
        if role:
            if role in selected:raise RuntimeError('Ambiguous own '+role+' process')
            selected[role]=(pid,a)
    if set(selected)!={'physics','guard','supervisor'}:raise RuntimeError('Wait for physics, guard and supervisor readiness')
    profile={'physics':{0,1,2,3},'guard':{4},'supervisor':{5}}
    if not set(range(6))<=os.sched_getaffinity(0):raise RuntimeError('This measured workstation profile needs CPUs0–5')
    records=[]
    for role,(pid,argv) in selected.items():
        path=Path('/proc')/str(pid)
        if (path/'cmdline').read_bytes().decode().rstrip('\0').split('\0')!=argv:
            raise RuntimeError('Scoped process changed before configuration')
        count=0
        for task in (path/'task').iterdir():
            try:os.sched_setaffinity(int(task.name),profile[role]);count+=1
            except ProcessLookupError:pass
        records.append(dict(role=role,pid=pid,cpus=sorted(profile[role]),threads_configured=count))
    report=seal(dict(scene_sha256=scene['sha256'],launch_pid=launches[0],processes=records,
        renderer_policy='unchanged background last-quarter CPUs',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    write_json(directory/'cpu-profile.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
