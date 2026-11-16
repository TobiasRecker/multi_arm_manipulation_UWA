# Preparing the first real carton test

The user requested a slow real test on2026-11-16 and will start the URs after
preparation. This preparation sends no power/brake/program, controller-switch,
arm-motion, gripper-activation or gripper-motion commands. Existing drivers,
simulations and camera services are preserved.

## Current evidence

- Both right URs report `POWER_OFF`, `NORMAL`, `ros.urp STOPPED`. Existing
  driver listeners remain available. No Dashboard write was sent.
- All four native RTDE output streams were read: actual joints/velocities,
  native TCP pose/wrench, active TCP offset, both speed-scaling factors and
  robot/program/safety state. The right arms currently report zero TCP offset.
- Robotiq URCap servers on both right URs answer GET requests on63352.
  Both report `ACT=0, STA=0, FLT=0`. This proves server readability, not
  gripper activation, physical opening or holding force.
- The new ROS read services were tested on the actual endpoints in monitor
  mode. Both returned status; both own nodes then exited cleanly without SET.
-23 focused software tests pass. A separate ROS integration in mock domain67
  passes monitor rejection, explicit activation/movement, raw-force-cap rejection
  and shutdown without automatic reset/open/force-zero. It uses a loopback
  register emulator; no real gripper was activated or moved.
- Individual factory FK agrees with the recorded native right TCP poses within
  0.001mm and0.000005rad. This is an internal kinematics/frame consistency
  check, **not independently measured physical accuracy or world registration**.

Evidence in workspace `setup/tasks/`:
`carton_hardware_preparation_20261116_01/`,
`carton_gripper_ros_mock_20261116_01/`,
`carton_gripper_ros_readonly_20261116_01/`.
Initial import/FK-development failures are retained in the corresponding logs;
the successful tests use explicit source paths and full world-to-base inversion.

## Read-only entry point

From the workspace root:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
python3 src/multi_arm_manipulation_UWA/tools/prepare_carton_hardware.py \
  --observe --output setup/tasks/NEW_UNIQUE_HARDWARE_OBSERVATION
```

This writes native observations and a preparation record. `prepared=true` is
not `motion_ready=true`. It never creates an executable hardware trajectory.
An offline bundle without device access is available by omitting `--observe`.
Before using observations for movement, acquire fresh data again. Native wrench
values require frame/payload/tare checks and are not measurements of individual
jaw clamping force. Raw GET status is sequential, not an atomic device snapshot.

For persistent ROS status, start one process per arm in separate sourced
terminals. They default to **MONITOR ONLY**, reject all command goals and send
only GET requests:

```bash
python3 src/multi_arm_manipulation_UWA/tools/carton_gripper_ros.py \
  --mode hardware --arm right_front
python3 src/multi_arm_manipulation_UWA/tools/carton_gripper_ros.py \
  --mode hardware --arm right_rear
```

Status: `/uwa_hardware/<arm>/gripper/status` (`std_msgs/msg/String`, JSON).
Read service: `/uwa_hardware/<arm>/gripper/read` (`std_srvs/srv/Trigger`).
Command action: `/uwa_hardware/<arm>/gripper/command`
(`uwa_cell_gripper_interfaces/action/RobotiqCommand`). There is one adapter
lease per arm/domain; another invocation does not replace the existing node.

## Explicit gripper commissioning after the operator starts the URs

First check the real grippers individually, with clear finger travel and no
carton load. Gripper activation itself can move fingers. It is never implied
by UR startup, opening the node, reading status or submitting MOVE.

The adapter's `--actuate` flag permits individual command goals; it still
sends no automatic activation or movement. Initial bounds are force raw0
and speed raw32. These are engineering starting settings, not measured N/mm/s.
No physical ACTIVATE/MOVE was executed during preparation.

`RobotiqCommand` goal fields:

| Field | Meaning |
| --- | --- |
| `operation: 2` | Explicit activation: reset ACT, wait inactive, set ACT, wait ready |
| `operation: 1` | Move an already activated, fault-free gripper |
| `position_raw` | Robotiq register0–255; no calibrated aperture conversion yet |
| `speed_raw` | Robotiq register0–255, constrained by configured cap |
| `force_raw` | Robotiq register0–255, constrained by configured cap; **not N** |
| `timeout_s` | Explicit1–30s confirmation deadline |

For later commissioning, a MOVE goal has the form:

```yaml
operation: 1
position_raw: 0
speed_raw: 16
force_raw: 0
timeout_s: 15.0
```

Do not infer a50N-per-jaw limit from `force_raw: 50` or from motor current.
[Robotiq explains that force settings/current thresholds and actual force vary](https://blog.robotiq.com/knowledge/how-works-the-force-for-the-grippers-5-1736280826249).
The transport follows the locally backed-up vendor URCap1.8.6 communication
scripts, including batched POS/SPE/FOR, three-byte `ack`, and object-detection
registers. It never uploads URScript or changes the robot program.

MOVE waits for requested-position acknowledgement and stable terminal object
status. Object detection does not prove four pad contacts or a supported load.
Timeout/disconnection/fault produces an unconfirmed/failed result without
automatic retry, reset or opening. Action cancellation is rejected: there is
no generic cancel-to-release behavior. Closing the node also leaves the device's
last target unchanged. This prototype is not a safety-rated finger stop;
physical stop behavior must be checked before loaded use. An arm stop must
retain the gripping target.

## Slow first-lift proposal and remaining live checks

`uwa_cell_tasks/config/carton_hardware_first_test.yaml` records the proposed
first stage:0.5mm/s object speed,5mm lift,1s dwell,0.005rad/s arm speed and
0.005rad/s² arm acceleration. These are starting values awaiting the actual
checked path. Grip force/speed mappings deliberately remain unset.

After UR startup, proceed with fresh read-only state/driver/sensor checks,
individual empty gripper commissioning, and a real model/object alignment.
Use the actual scene before preparing an approach; no stored simulation Home
or object pose is an executable hardware target. Current world/table/base
anchors are provisional, as documented by the parallel four-arm geometry work.

The carrying-arm hardware execution path still needs integration/qualification.
The existing hardware PTP runner permits independent progress and is unsuitable
for a rigid loaded grasp. Two separate scaled trajectories with matching start
timestamps do not establish a common object law. Native scaling depends on
both `speed_scaling` and `target_speed_fraction`;
[UR's controller documentation](https://docs.universal-robots.com/Universal_Robots_ROS_Documentation/rolling/doc/ur_robot_driver/ur_controllers/doc/index.html)
describes this behavior. Keep one shared object path/time law, frozen actual
object-to-TCP offsets, measured relative-pose checks and group stopping before
attempting the loaded lift. No hardware execution switch was added to the
simulation-only `cell_task` command.

Thus the prepared software is ready for **live commissioning/observation**, not
an immediate automatic two-arm carton lift. Powering on the URs starts no task.
