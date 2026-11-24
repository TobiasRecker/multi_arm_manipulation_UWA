"""Normal gripper program commands; no arm or gripper safety monitoring."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path

from uwa_cell_gripper_control.client import GripperClient
from uwa_cell_motion.common import dump
from uwa_cell_motion.execution import motion_context
from .motion_review import ReviewStore
from .carton_review import contact_component


def run(args, state_bytes, state):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    arms = ('right_front', 'right_rear')
    report = dict(success=False, phase=args.phase.upper(), protection_backend='minimal',
                  state=str(args.state.resolve()), state_sha256=hashlib.sha256(state_bytes).hexdigest(),
                  arm_commands=[], finger_commands=[], results={},
                  gripper_monitoring='none; collision geometry only',
                  segments=state.get('segments', []))
    def save():
        dump(output/'result.json', report)
    save()
    review = None
    if args.review_id:
        review = ReviewStore()
        component = contact_component(report['state_sha256'],args.review_image_sha256,args.start_ros_programs)
        review.begin_component(args.review_id,component,'contact')
        report['review_id'] = args.review_id
    if not args.execute:
        report.update(success=True,phase='READ_ONLY_READY_NO_COMMANDS')
        save()
        return 0
    if args.start_ros_programs:
        # Contact already follows a completed arm trajectory. The ordinary
        # startup request remains explicit; it never resets native safety.
        import tempfile
        from uwa_cell_motion.common import config
        from uwa_cell_motion.hardware_model import HardwareProblem
        from uwa_cell_motion.minimal_execution import MinimalHardwareClient
        from .minimal_reviewed_execution import start_programs
        repo = Path(__file__).resolve().parents[2]
        with motion_context(), tempfile.TemporaryDirectory(prefix='minimal-contact-start-') as directory:
            problem = HardwareProblem(directory,config(repo/'uwa_cell_motion/config/hardware_carton_supported_trend.yaml'),
                                      repo/'config/hardware_inventory.yaml')
            client = MinimalHardwareClient(problem,'hardware')
            try:
                report['program_start'] = start_programs(client,output,arms,
                    review=(args.review_id,component,'contact') if review else None,
                    scene=None if review else ReviewStore().status()['session_id'])
            finally:
                client.destroy_node()
    def command(arm):
        with GripperClient(arm) as client:
            if args.phase == 'prepare':
                activation = client.activate()
                return dict(activation=activation, result=client.open(force_raw=0,speed_raw=16))
            result = (client.close_gripper(force_raw=0,speed_raw=16) if args.phase == 'close'
                      else client.open(force_raw=0,speed_raw=16))
            return dict(result=result)
    try:
        report['finger_commands'] = [dict(arm=arm,operation=args.phase,force_raw=0,speed_raw=16) for arm in arms]
        save()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {arm:pool.submit(command,arm) for arm in arms}
            for arm,future in futures.items():
                try:
                    report['results'][arm] = future.result()
                except Exception as error:
                    report.setdefault('errors',{})[arm] = str(error)
        report['success'] = not report.get('errors')
        report['gripper_commands_completed'] = report['success']
        report['phase'] = ({'prepare':'ACTIVE_OPEN_HELD','close':'GRIPPER_CLOSE_COMPLETED',
                            'release':'GRIPPER_OPEN_COMPLETED'}[args.phase]
                           if report['success'] else 'GRIPPER_COMMAND_FAILED')
        # No inferred contact, grip strength or stationary-arm claim.
        return 0 if report['success'] else 1
    finally:
        save()
