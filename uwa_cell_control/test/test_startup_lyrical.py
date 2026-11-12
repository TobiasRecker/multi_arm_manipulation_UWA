"""Exercise MATCH startup warning paths with Lyrical's actual logger API."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from ament_index_python.packages import get_package_prefix
from rclpy.impl.rcutils_logger import RcutilsLogger


def startup():
    path=Path(get_package_prefix('mur_launch_hardware'))/'lib/mur_launch_hardware/ur_startup_enable.py'
    spec=importlib.util.spec_from_file_location('tested_ur_startup_enable',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.URStartupEnable


def logger():
    # Deliberately exposes only supported methods; no deprecated warn alias.
    entries=[]
    return SimpleNamespace(info=entries.append,error=entries.append,warning=entries.append),entries


def test_setmode_reached_target_warning_does_not_abort_startup():
    assert hasattr(RcutilsLogger,'warning')
    log,entries=logger()
    answer=SimpleNamespace(success=False,message='Reached target robot mode; program is not running')
    done=SimpleNamespace(result=lambda:SimpleNamespace(result=answer))
    handle=SimpleNamespace(accepted=True,get_result_async=lambda:done)
    future=SimpleNamespace(result=lambda:handle)
    client=SimpleNamespace(wait_for_server=lambda **kwargs:True,send_goal_async=lambda goal:future)
    node=SimpleNamespace(_client=client,_wait_timeout=1.,_target_robot_mode=7,
        get_logger=lambda:log,_wait_for_future=lambda *args:True)
    assert startup()._send_set_mode(node,False,True)
    assert any('reached the requested robot mode' in entry for entry in entries)


def test_program_running_timeout_reports_warning_instead_of_attribute_error():
    log,entries=logger()
    node=SimpleNamespace(_program_running_client=SimpleNamespace(call_async=lambda request:object()),
        _service_timeout=1.,_wait_for_future=lambda *args:False,get_logger=lambda:log)
    assert startup()._call_program_running(node) is None
    assert any('timed out' in entry for entry in entries)
