"""Pure request normalization; physical force/aperture mappings are not assumed."""
import math

ARMS=('left_front','left_rear','right_front','right_rear')
OPEN,CLOSE,SET_OPENING,ACTIVATE=1,2,3,4


def nominal_opening_percent(width_mm):
    """2F-85 nominal85mm stroke; approximate aperture, not measured width."""
    if not math.isfinite(width_mm) or not 0<=width_mm<=85:
        raise ValueError('Nominal 2F-85 width must be0..85mm')
    return width_mm*100/85


def nominal_force_raw(force_n):
    """Linear nominal scale over the vendor20..235N range, NOT a force model.

    Actual force/current relation is nonlinear and depends on contact/speed.
    Sources and limits: docs/gripper_ros_api.md, nominal setpoints section.
    """
    if not math.isfinite(force_n) or not 20<=force_n<=235:
        raise ValueError('Nominal 2F-85 force must be20..235N')
    return int(math.floor((force_n-20)*255/215+.5))


def endpoint(arm, mode):
    if arm not in ARMS or mode not in ('hardware','mock'):
        raise ValueError('Known cell arm and hardware/mock mode required')
    return ('/uwa_hardware/' if mode=='hardware' else '/uwa_gripper_mock/')+arm+'/gripper'


def raw_target(operation, opening_percent):
    if not math.isfinite(opening_percent):raise ValueError('Opening must be finite')
    if operation==OPEN:return 0
    if operation==CLOSE:return 255
    if operation==ACTIVATE:return 0
    if operation!=SET_OPENING:raise ValueError('Unknown gripper operation')
    if not 0 <= opening_percent <= 100:raise ValueError('Opening percent must be0..100')
    return int(math.floor((100-opening_percent)*255/100+.5))


def normalize(request):
    target=raw_target(request.operation,request.opening_percent)
    # The existing raw transport deliberately keeps activation separate.
    return (2 if request.operation==ACTIVATE else 1,target,request.speed_raw,
            request.force_raw,request.timeout_s)


def capabilities(arm, mode, enabled, force_cap, speed_cap):
    return dict(arm=arm,mode=mode,endpoint=endpoint(arm,mode),actuation_enabled=enabled,
        operations=['open','close','set_opening','activate'],
        opening_unit='percent of nominal raw-register stroke:100=open,0=closed',
        force_unit='raw0..255; not newtons',speed_unit='raw0..255; not mm/s',
        physical_force_calibrated=False,physical_width_calibrated=False,
        max_force_raw=force_cap,max_speed_raw=speed_cap,
        automatic_activation=False,automatic_release=False,
        cancellation_supported=False,
        command_action='operate',legacy_raw_action='command',status_service='read')
