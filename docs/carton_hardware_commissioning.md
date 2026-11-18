# Preparing the first real carton test

**18 November:** both right URs reached real unloaded150mm pregrasp poses
using a fresh carton observation, the current focus107 OAK fit and fixed
user-adopted base bindings. Command speed remained0.1rad/s. Both final holds
and independent stationary windows passed; final image reviewed. Grippers
remain open/inactive, with no finger commands or contact/lift attempt. Evidence:
`setup/tasks/carton_pregrasp_20261118_completed/`. This supersedes the17November
alignment failure below. Loaded cooperative hardware execution remains separate.


**17 November update:** the first unloaded right-front approach completed at
0.015rad/s command speed, followed by a confirmed hold. The fresh OAK image
failed the carton-alignment review. All arms remain held, grippers open in
monitor mode; no descent, rear approach, grasp or lift was attempted. Board
diagnostics suggest a roughly6.3degree error in the preliminary camera reference;
no replacement calibration has been activated. See
[the current commissioning record](../work/carton-hardware-commissioning.md).
Earlier statements below that no arm target was sent are historical.

For agent-facing gripper commands, use the shared four-arm
[ROS gripper API](gripper_ros_api.md): persistent service, named actions,
Python/CLI helpers and explicit units. The earlier two-arm raw adapter below
remains compatible and shares the same process ownership lease.

Update17November: a separate unloaded test activated and opened all four
grippers and verified SPE16/FOR0 using separate writes with readback before
changing POS. This supersedes the16November "not activated" status below.
The carrying-arm backend, jaw force mapping and loaded grasp remain unqualified.
The earlier readiness index's gripper-code hash is obsolete. See the
[real commissioning results](hardware_commissioning_2026-11-17.md).

The user requested a slow real test on2026-11-16 and will start the URs after
preparation. The16November preparation was read-only. After the explicit
17November handoff, four individual unloaded finger goals were executed through
the shared ROS service, as recorded below. No arm-motion, controller-switch,
power/brake/program or activation command was sent by this carton thread.

## Handoff observation,17November

The operator explicitly released the right arms ("Jetzt frei"). A fresh
read-only check found both RUNNING/NORMAL, remote, `ros.urp PLAYING` and reverse
connections established. All four native output streams were stationary in the
observed window. Both right `collision_hold_controller`s own the six position
interfaces; their motion controllers are inactive. This initial handoff check
sent no hold/reset/controller or gripper write.

The managers currently use default FastDDS transport. A client forced to UDPv4
timed out; the same read-only controller query with the managers' default
transport succeeded. No driver restart or configuration change was necessary.

Both right grippers now report ACT1/STA3/FLT0/OBJ3/POS3/PRE0. The sequential
GET snapshot recorded RF SPE0/FOR16 and RR SPE0/FOR0; the separate commissioning
report recorded SPE16/FOR0. These are observations at different times, not
calibrated jaw forces or evidence that settings remain unchanged. Read them
again before any explicit move and verify requested FOR/SPE before POS.

The existing OAK photo service captured native8K/focus116 at10:31:25+08:00:
`setup/oak4/photos/20261117-103125-standard-abdf393d/standard.png`.
The carton is visually back at its previous location. Offline single-frame
localization has69inliers/2.458px reprojection RMS. Preliminary world conversion
gives1.43deg upright tilt. This is a plausible geometry candidate, **not verified
absolute grasp accuracy or manipulation approval**. The camera was closed after
capture. Evidence: `carton_hardware_preparation_20261117_01/` and
`carton_hardware_handoff_20261117_01/` under workspace `setup/tasks/`.

A new transport-free `hardware_object_reference.SharedObjectReference` passes
14focused tests: one object path/clock using the minimum native effective
scaling, fixed copied grasp offsets, source freshness, relative-pose checking,
group fault latching and no resume/open. It emits reference/stop requests only;
there is **no real IK/command-delivery/stop-confirmation port**. Those software
tests are not a hardware motion or loaded-stop qualification. No shared task
package rebuild was performed during the parallel simulation campaign.

## Real ROS empty partial travel and offline approach,17November

Both right grippers completed **raw0 →128 →0**, one arm at a time, with
SPE16/FOR0. All four action goals were accepted and succeeded; partial targets
returned POS128/PRE128/OBJ3, open targets POS3/PRE0/OBJ3. ACT1/STA3/FLT0 remained
confirmed and no contact was reported. The shared `uwa-grippers.service` was
explicitly enabled with caps force0/speed16 for these goals, then returned to
**MONITOR ONLY** with the same caps. No ACTIVATE, arm, controller or Dashboard
command was issued. This is partial empty register travel, not full-stroke
metrology, N/mm calibration, a finger-stop test or a loaded grip.

The reusable harness `tools/commission_carton_grippers.py` defaults to read-only,
uses the existing ROS services/action, checks a fresh stationary native arm
posture against the saved unloaded handoff, and requires explicit
`--execute-empty-stroke` for those four goals. Unexpected contact or uncertain
outcome aborts without automatic open/retry/reset. An earlier attempt to start
a duplicate legacy adapter was rejected by the shared device lease before any
goal; the harness was changed to reuse the central interface. Failure retained.

Evidence under workspace `setup/tasks/`:

- `carton_gripper_ros_handoff_20261117_02/result.json`: shared read-only check.
- `carton_gripper_ros_empty_stroke_20261117_01/result.json`: four real goals.
- `carton_hardware_post_gripper_20261117_01/observations.json`: all four arms
  observed stationary afterwards, both right grippers open/SPE16/FOR0/FLT0.
- `carton_gripper_ros_mock_20261117_01/result.json`: ROS loopback regression
  after the separate FOR/SPE readback correction. Its expected write sequence
  was updated from the obsolete batched protocol.

`tools/prepare_carton_pregrasp.py` rebuilds object-local contact-design points
from the fresh camera pose and hardware factory kinematics. It includes the
carton meshes, complete unknown-opening tool envelopes, full FCL checks and
unchanged neighbor stop reserves. The third offline case finds a serial
RF-then-RR path to the80mm pregrasp positions; both segments were replayed at
≤0.005rad sampling. Initial two bounded searches found no path and remain
preserved. Adding equivalent joint winding choices near the measured start
removed unnecessary complete rotations; FK target poses were reverified.
No timing, descent or hardware-executable trajectory was exported.

`carton_hardware_pregrasp_20261117_03/evidence.json` records this **geometric
candidate only** (`executable=false`, `hardware_plan=false`). The single-image
world pose and provisional bases still need physical alignment. Twenty-four
focused tests pass (14common-object reference +10pregrasp strategy/frame/winding
cases), log `setup/logs/carton-hardware-reference-pregrasp-tests02-20261117.log`.

## Historical preparation evidence,16November

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

For persistent ROS status, reuse the central service; do not start a second
legacy adapter against its device lease. Default monitor mode rejects command
goals and sends only GET requests:

```bash
bash src/multi_arm_manipulation_UWA/scripts/grippers.sh monitor
ros2 run uwa_cell_gripper_control cell_gripper --arm right_front status
ros2 run uwa_cell_gripper_control cell_gripper --arm right_rear status
```

Status: `/uwa_hardware/<arm>/gripper/status` (`std_msgs/msg/String`, JSON).
Read service: `/uwa_hardware/<arm>/gripper/read` (`std_srvs/srv/Trigger`).
Command action: `/uwa_hardware/<arm>/gripper/command`
(`uwa_cell_gripper_interfaces/action/RobotiqCommand`). There is one adapter
lease per arm/domain; another invocation does not replace the existing node.
See [the shared ROS API](gripper_ros_api.md) for capabilities and explicit mode
changes. The old source-tree adapter remains a compatibility/testing entry.

## Explicit gripper commissioning after the operator starts the URs

First check the real grippers individually, with clear finger travel and no
carton load. Gripper activation itself can move fingers. It is never implied
by UR startup, opening the node, reading status or submitting MOVE.

The adapter's `--actuate` flag permits individual command goals; it still
sends no automatic activation or movement. Initial bounds are force raw0
and speed raw32. These are engineering starting settings, not measured N/mm/s.
The16November preparation sent no ACTIVATE/MOVE; the17November partial empty
MOVE test is recorded above. No activation was needed in that test.

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
scripts, three-byte `ack`, and object-detection registers. Actual17November
commissioning supersedes the earlier batched-write implementation: FOR and SPE
are now written separately and confirmed twice before POS/GTO. An ACK alone
does not prove the parameters were accepted. It never uploads URScript or
changes the robot program.

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
0.005rad/s² arm acceleration. These are historical engineering proposals, not
an executable timing profile. The current real guard uses0.003rad/s; the0.005
proposal cannot be sent under it. The separate unloaded test also saw native
velocity peaks above its command bound. Before arm travel, select/verify a
lower command profile against the existing monitored bound and recompute the
complete trajectory/reserves; do not simply raise the guard to this proposal.
Grip force/speed physical mappings deliberately remain unset.

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
