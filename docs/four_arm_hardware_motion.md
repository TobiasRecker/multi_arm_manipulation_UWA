# Four-arm hardware collision guard and PTP

Implemented November16,2026. This backend uses the existing four MATCH UR
drivers in domain66, with a separate GenericSystem/mock backend in domain67.
The [Gazebo backend](four_arm_motion.md) remains restricted to domain64 and
`uwa_cell_sim`. **Hardware stopping distances and timing have not been measured.**
No real driver, program or arm was operated during this implementation.

## State and stopping

The10Hz geometry process reads each UR's output-only RTDE stream directly:
device timestamp, six actual joint positions/velocities and native robot,
program and safety state. Repeated device timestamps do not refresh state;
buffered samples retain their age, and clock resets latch faults. The model
must match all six factory joint origins advertised by each ROS driver.
Missing/stale arm state blocks that arm and its two monitored neighbors.

Exactly LF↔RF, LF↔LR, RF↔RR and LR↔RR are monitored. Distances are between
sphere surfaces. Relative link-motion bounds, source age, check interval,
stop latency, braking and model margin determine each pair threshold/lease.
The supervisor checks leases on monotonic real time, independently of ROS
simulation time. A separate watchdog stops on supervisor loss; watchdog loss
also latches the supervisor. These are separate processes in the launch file.

An armed stop cancels trajectory/native-mode actions and switches the affected
manager to `uwa_cell_motion/CollisionHold`. The plugin claims the **six actual
arm position interfaces**, decelerates from measured state and holds indefinitely.
The adapter checks hardware plugin identity, live joint/deceleration parameters
and interface ownership, and removes other arm command owners, including
velocity, force, freedrive and passthrough controllers. It never commands a
gripper. An incompatible manager/configuration cannot be reported as held.
Topic commands and conflicting controller activation cannot displace a
position hold. A controller using another command interface is removed on
inspection; this is a polled software interlock, not an unbypassable hardware
inhibit against another privileged controller-manager client.

Manager/hold failure or missing measured standstill triggers a separate native
Dashboard **`stop` only** fallback. It never powers, releases brakes, loads or
plays programs, acknowledges protective stops or opens tools. Each arm has its
own measured standstill result; resource ownership alone is not confirmation.
Stopped pairs stay latched until explicit stationary/clear reset. Reset may
release an independent healthy subset and never resumes a trajectory/program.

Default `config/hardware_motion.yaml` is an **unmeasured engineering profile**:
0.01rad/s,0.02rad/s²,1.0s assumed stop latency,0.2rad/s² assumed braking,
40mm model reserve,200ms state age,250ms heartbeat. These numbers are not
physical acceptance results. Other PC command sources must obey the same speed
envelope; detecting excess velocity does not prove reserve for arbitrary faster
external motion. Pendant programs are outside the regular ROS hold path.
Native STOP depends on the network and UR control mode; a response is not a
standstill measurement. PC/network/power loss and real stop response remain to
be qualified separately from the independent hardware emergency stop.

## Geometry

The central calibrated cell layout and each inventory factory kinematics file
are used, including different UR types, tables and cameras. World/table anchors
remain provisional. Because real finger telemetry is unavailable, moving tool
bodies use conservative whole-volume sphere unions over **the entire modeled
opening range**. Analytic motion inflation covers openings between samples.
There are166 spheres per arm in the current model. Unknown moving fingers are
hidden visually; the envelope remains visible in guard markers.

Opening sweeps of links in the **same coupled Robotiq mechanism** overlap at
mutually exclusive openings. These internal link pairs are explicitly allowed
in both Python MoveIt and the native RRT SRDF. This does not qualify internal
gripper mechanics. Tool↔arm, camera, table and other-arm collisions remain
checked. `check-model` exports this policy, model binding and mesh hashes.
`/uwa_cell/joint_states` contains24 actual arm joints; virtual envelope
coordinates exist only on `/uwa_cell/model_joint_states` for visualization.

## Build and monitor

From `~/UWA_ws`, build the package in the existing Lyrical overlay:

```bash
source setup/lyrical_env.bash
colcon --log-base log_lyrical build --build-base build_lyrical \
  --install-base install_lyrical --packages-select uwa_cell_motion --symlink-install
```

Existing MATCH drivers must be running, with the new plugin discoverable in
their installation environment. Use the [common UR bringup](ur_bringup.md) for
separately requested preparation. This backend starts no drivers or UR programs.

```bash
bash src/multi_arm_manipulation_UWA/scripts/hardware_motion.sh monitor rviz:=true
bash src/multi_arm_manipulation_UWA/scripts/hardware_motion.sh status
```

Monitor reads output states, robot descriptions and manager metadata but sends
**no controller switches, goals or native STOP**. Labels say `MONITOR ONLY`
and `Would-stop`; this mode provides no active stopping. RViz uses the hardware
model, guard spheres/closest points and independent interlock text. Inspect
`/uwa_cell/collision_guard/decision`, `/uwa_cell/collision_supervisor/status`
and `/uwa_cell/hardware_watchdog/status` for live decisions. Process-active
status alone is not a health indication. Drivers launched with UDPv4 require
clients to inherit `FASTDDS_BUILTIN_TRANSPORTS=UDPv4` as in their bringup.

## Explicit arming and recovery

After reviewing the physical commissioning setup, provision inactive holds and
explicitly arm. **Arming stops/latches all arms at startup.** It does not move
them to another pose. These commands are documented for commissioning; they
were not executed on physical robots in this task.

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 run uwa_cell_motion cell_hardware_motion --mode hardware provision
bash src/multi_arm_manipulation_UWA/scripts/hardware_motion.sh arm rviz:=true
# Only after fresh state, clear distances and confirmed standstill:
ros2 run uwa_cell_motion cell_hardware_motion --mode hardware reset
```

`hardware_motion.sh halt` requests all native program stops, action cancellation
and resource holds, then reports measured standstill if fresh feedback exists.
`hardware_motion.sh stop` first does that for an armed service and only closes
it after confirmation; if unconfirmed, the service stays running. Closing a
monitor service sends no stop. Armed service exit also attempts native STOP
through a small helper independent of ROS/MoveIt/kinematics initialization:

```bash
ros2 run uwa_cell_motion native_hardware_stop --mode hardware \
  --inventory src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml
```

The helper reports acknowledgements and explicitly leaves standstill
unconfirmed. It is a fallback for a running PC, not a remedy for PC failure.
After native program STOP, program preparation remains a separate operator
action; reset does not press Play or clear a native safety stop.

## Plan, preview, execute

The actual complete start state comes from the guard. A request contains
`start` and `goals`, e.g. `"right_rear": [six joint angles in radians]`.
Cartesian goal schema is shared with the [simulation guide](four_arm_motion.md);
an explicit frame is required and target links must be rigidly attached to
`tool0`. Resolve common Cartesian goals once for a fair planner comparison.
Unselected arms remain measured stationary obstacles. Tools are not actuated.

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 run uwa_cell_motion cell_hardware_motion --mode hardware snapshot --output /tmp/hardware-request.json
# Edit goals in the request, retain the complete measured start/model binding.
ros2 run uwa_cell_motion cell_hardware_motion --mode hardware plan /tmp/hardware-request.json \
  --method rrtconnect --seed 0 --output /tmp/hardware-plan.json
# Alternatively: --method circular, with the same request and limits.
ros2 run uwa_cell_motion cell_hardware_motion --mode hardware preview /tmp/hardware-plan.json \
  --output /tmp/hardware-preview.html
# Explicit real motion, only during separately prepared physical commissioning:
ros2 run uwa_cell_motion cell_hardware_motion --mode hardware execute /tmp/hardware-plan.json \
  --output /tmp/hardware-execution.json
```

Plan and HTML preview send no motion; the preview shows joint/time curves,
backend and unmeasured reserve. A simulation/mock plan is rejected for hardware
execution. Inventory, model, limits, mesh hashes, actual start and timing are
rechecked before activation. There is no automatic reposition to a plan start.
Selected driver JointStates must agree with independent actual RTDE, and their
native robot/program must be ready; this changes no existing manual GUI gates.

Both planners use the same full-cell MoveIt collision scene and final timing
validation. RRTConnect plans the combined selected joint space; the circular
baseline has no RRT fallback. Multiarm execution uses measured progress and
validated independent-progress phases; UR speed scaling does not establish
synchronization by matching timestamps. After a pair stop, remaining paths are
rechecked against stopped arms and braking envelopes; unsafe remainders stop.

## Evidence and remaining physical work

The current evidence is under `~/UWA_ws/setup/logs/`:

- `uwa-hardware-motion-build.log`, `uwa-hardware-motion-tests.log`: Lyrical build
  and package tests, including existing simulation regressions.
- `uwa-hardware-mock-integration-current.json`: isolated four-manager ROS
  integration, monitor without actuation; pair/multiple/stale/clocked source
  faults, partial reset, reactivation/topic suppression, wrong plugin/hold
  bounds, geometry/supervisor/watchdog loss, and both planner execution paths.
- `uwa-hardware-hold-plugin-check.json`: actual ros2_control GenericSystem and
  C++ six-joint hold, interface conflict rejection and removal of a velocity
  owner. The private test unit was stopped afterwards.

Earlier unsuccessful mock attempts remain recorded; fake-manager dynamics
and GenericSystem are not UR braking measurements. No hardware guard was armed
and no real STOP/fahrgoal was sent in this task. Next physical qualification:
measure detection/source/switch/native-stop latency and braking per UR, test
pair/independent-arm continuation and process/network faults, verify modeled
tools/anchors, then replace engineering assumptions with measured reserves.
