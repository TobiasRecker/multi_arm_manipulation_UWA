"""Headless owner client for complete runs and reproducible interruption tests."""
import argparse,os,signal,threading,time,json
import rclpy
from rclpy.executors import SingleThreadedExecutor
from .client import Client
from uwa_cell_gazebo.configuration import ROBOT_IDS


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--robots',nargs='+',choices=ROBOT_IDS,default=list(ROBOT_IDS))
    p.add_argument('--samples',type=int,default=40)
    p.add_argument('--apply',action='store_true')
    p.add_argument('--stop-after',type=float)
    p.add_argument('--pause-after',type=float)
    p.add_argument('--resume-after',type=float,default=2.)
    p.add_argument('--disconnect-after',type=float,help='Stop heartbeats to test owner loss')
    args=p.parse_args()
    if os.environ.get('ROS_DOMAIN_ID')!='64':p.error('Source scripts/env.bash; domain 64 required')
    rclpy.init();node=Client();executor=SingleThreadedExecutor();executor.add_node(node)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
    interrupted=threading.Event();signal.signal(signal.SIGINT,lambda *_:interrupted.set())
    deadline=time.monotonic()+15
    try:
        while not node.prepare_client.service_is_ready() and time.monotonic()<deadline:time.sleep(.1)
        future=node.prepare(args.robots,args.samples)
        if future is None:raise RuntimeError(node.error)
        while not future.done():time.sleep(.05)
        if not future.result().accepted:raise RuntimeError(future.result().message)
        last='';started=None;paused_at=None;paused_once=False;stop_sent=False;disconnected=False;applying=False
        while True:
            if node.error:raise RuntimeError(node.error)
            state=node.state;phase=state.get('phase','')
            message=f"{phase} {state.get('robot_id','')} {state.get('accepted',0)}/{state.get('target',0)} {state.get('message','')}"
            if message!=last:print(message,flush=True);last=message
            if interrupted.is_set() and not stop_sent:node.command('stop');stop_sent=True
            if phase=='READY' and started is None:
                node.start();started=time.monotonic()
            if started:
                elapsed=time.monotonic()-started
                if args.stop_after and elapsed>=args.stop_after and not stop_sent:node.command('stop');stop_sent=True
                if args.disconnect_after and elapsed>=args.disconnect_after and not disconnected:
                    for timer in list(node.timers):node.destroy_timer(timer)
                    disconnected=True
                if args.pause_after and elapsed>=args.pause_after and not paused_once:
                    node.command('pause');paused_once=True
                if phase=='PAUSED':
                    paused_at=paused_at or time.monotonic()
                    if time.monotonic()-paused_at>=args.resume_after:node.command('resume')
            if phase in ('ERROR','STOPPED'):
                if stop_sent or disconnected:return 0
                raise RuntimeError(state.get('message',phase))
            if node.result is not None and not node.result.success:raise RuntimeError(node.result.message)
            if phase=='COMPLETE' and node.result is not None:
                print('RESULT',state.get('result_path'),flush=True)
                if args.apply and not applying:node.apply();applying=True
                elif not args.apply or state.get('active_profile'):
                    print(json.dumps({k:state.get(k) for k in ('result_path','relative_bases','ground_truth','active_profile')},indent=2));return 0
            time.sleep(.1)
    finally:
        if node.state.get('phase') in ('MOVING','RUNNING','PREPARING','CAPTURING','SETTLING','RETURNING','PAUSED','SOLVING'):
            node.command('stop');time.sleep(.5)
        executor.shutdown(timeout_sec=2);node.destroy_node();rclpy.shutdown();thread.join(timeout=2)
