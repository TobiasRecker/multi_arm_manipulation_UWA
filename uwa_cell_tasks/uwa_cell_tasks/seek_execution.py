"""Execute one bounded search in an isolated Gazebo task runner."""
import json
import threading
from pathlib import Path

import numpy as np
from action_msgs.msg import GoalStatus
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String

from .box_drawing import SURFACES
from .core import write_json


def execute_seek(sim, probe, trajectory, directory, store):
    directory = Path(directory)
    spec = probe.spec
    scene = probe.problem.scene_record
    axis, sign = SURFACES[spec.face]
    walls = {f'shell_{i}' for i, shape in enumerate(scene['shapes'])
             if shape['axis']==axis and shape['side']==int(sign>0)}
    walls.add('probe_surface_patch')
    records = []
    lock = threading.Lock()
    hit = threading.Event()
    phase = 'tare'
    bias = None
    hit_index = None
    report = dict(outcome='measurement_unavailable', recipe=spec.record(), workpiece_frame='carton_center')

    def receive(msg):
        nonlocal hit_index
        window = json.loads(msg.data)
        positions = window.get('probe_positions', {})
        joint = window['joint_reactions'].get(spec.sensor_joint, {})
        raw = joint.get('mean_force_n', [None]*3)[2]
        valid = (raw is not None and np.isfinite(raw) and
                 joint.get('frame')=='joint:'+spec.sensor_joint and
                 window.get('probe_samples',0)==window['physics_samples'] and
                 abs(window['window_duration_s']-.010)<1.e-6 and
                 all(np.isfinite(positions.get(j,np.nan)) for j in probe.names))
        # Contact pairs are diagnostic only. The transition below uses the wrist.
        loads = []
        for pair in window['contact_loads']:
            a,b = sorted(pair['collisions'],key=lambda c:'uwa_grasp_carton' not in c)
            if 'uwa_grasp_carton' in a and a.split('::')[-1] in walls and 'probe_tip' in b:
                loads.append(pair['mean_normal_load_n'])
        with lock:
            if records and window['stamp'] <= records[-1]['stamp']:
                return
            row = dict(stamp=window['stamp'],start=window['window_start_s'], valid=bool(valid),
                       phase=phase, positions=positions, raw_z_n=raw, peak_z_n=window.get('probe_peak_z_n'),
                       pair_mean_n=sum(loads), pair_data_valid=not(window['missing_wrenches'] or window['invalid_wrenches']))
            records.append(row)
            if phase=='search' and valid and row['start'] >= search_start and hit_index is None and raw-bias >= spec.threshold_n:
                hit_index = len(records)-1
                hit.set()

    subscription = sim.create_subscription(String,'tasks/forces',receive,qos_profile_sensor_data)
    try:
        tare_start = sim.now()
        def tare_samples():
            with lock:
                return [r['raw_z_n'] for r in records if r['start']>=tare_start and r['valid']]
        sim.wait(lambda:len(tare_samples())>=5,5.)
        bias = float(np.mean(tare_samples()[-5:]))
        report['tare_z_n'] = bias
        search_start = sim.now()
        phase = 'search'
        (handle,) = sim.accept_goals([sim.send_goal('rigid_object_controller', trajectory)])
        result = handle.get_result_async()
        sim.wait(lambda:hit.is_set() or result.done(),trajectory['duration_s']*12+20.)
        sim.check_cancel()
        if not hit.is_set():
            answer = result.result()
            sim.handles.remove(handle)
            if answer.status != GoalStatus.STATUS_SUCCEEDED or answer.result.error_code:
                report['outcome'] = 'controller_error'
                raise RuntimeError('Search controller: '+answer.result.error_string)
            # Consume the last measured window before deciding the terminal result.
            end_stamp = sim.now()
            sim.wait(lambda:records and records[-1]['stamp']>=end_stamp,3.)
            if not hit.is_set():
                samples = [r for r in records if r['phase']=='search' and r['start']>=search_start]
                covered = (samples and all(r['valid'] for r in samples) and
                           all(b['stamp']-a['stamp']<.01001 for a,b in zip(samples,samples[1:])))
                report['outcome'] = 'travel_exhausted' if covered else 'measurement_unavailable'
            else:
                report['outcome'] = 'search_completed_before_cancel'
            raise RuntimeError('seek_contact: '+report['outcome'])

        # Await the terminal state as well as the cancellation acknowledgement.
        phase = 'cancel'
        cancel = handle.cancel_goal_async()
        sim.wait(cancel.done,5.)
        sim.wait(result.done,5.)
        if not cancel.result().goals_canceling or result.result().status!=GoalStatus.STATUS_CANCELED:
            report['outcome'] = 'controller_error'
            raise RuntimeError('Search goal did not finish canceled after contact')
        sim.handles.remove(handle)
        terminal_stamp = sim.now()
        sim.wait(lambda:records and records[-1]['stamp']>=terminal_stamp and records[-1]['valid'],3.)
        with lock:
            terminal = records[-1].copy()
            contact = records[hit_index].copy()
        measured = dict(sim.q, **terminal['positions'])
        report.update(outcome='contact_found',hit=probe.observation(contact['positions']),
                      hit_stamp=contact['stamp'],hit_force_n=contact['raw_z_n']-bias,
                      handoff=probe.observation(measured),handoff_stamp=terminal['stamp'],
                      handoff_joints=terminal['positions'])
        # Compile the checked return from actual feedback before submitting it.
        phase = 'retract'
        retract,_ = probe.leg('probe_retract',measured,spec.clearance_m,contact=True,target_state=probe.pre)
        write_json(directory/'drawing-trajectories/probe_retract.json',retract)
        store.event('RUNNING','move_object',step='probe_retract',hit_stamp=contact['stamp'])
        sim.follow(retract)
        report['retract'] = dict(controller='succeeded', **probe.observation(sim.q))
    except BaseException as error:
        if (sim.stop_directory/'STOP').exists() or isinstance(error,KeyboardInterrupt):
            report['outcome'] = 'operator_canceled'
        report['error'] = str(error)
        raise
    finally:
        sim.destroy_subscription(subscription)
        with lock:
            samples = list(records)
        trace = []
        for row in samples:
            if row['valid'] and bias is not None:
                trace.append(dict(stamp=row['stamp'],phase=row['phase'],force_n=row['raw_z_n']-bias,
                                  peak_n=row['peak_z_n']-bias,pair_mean_n=row['pair_mean_n'],
                                  pair_data_valid=row['pair_data_valid'], **probe.observation(row['positions'])))
        report['samples'] = len(trace)
        if trace:
            report['peak_n'] = max(row['peak_n'] for row in trace)
        if 'hit' in report:
            after = [r for r in trace if r['stamp']>=report['hit_stamp']]
            report['overtravel_m'] = max(r['travel_m'] for r in after)-report['hit']['travel_m']
            report['tip_wall_observed_at_hit'] = any(r['pair_data_valid'] and r['pair_mean_n']>0 and
                abs(r['stamp']-report['hit_stamp'])<.01001 for r in trace)
        write_json(directory/'seek-force-trace.json',trace)
        write_json(directory/'seek-result.json',report)
    return report
