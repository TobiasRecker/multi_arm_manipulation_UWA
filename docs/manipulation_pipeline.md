# Object-led manipulation skills (simulation)

The first recipe is `avocado_carton`, `right_front` + `right_rear`, empty rigid
carton, 30 mm lift, two-second dwell, set down and release. The task transport
cannot address hardware. It requires domain64, `uwa_cell_sim`, LOCALHOST and an
isolated `/uwa_grasp_*` namespace. No real power, brake or program commands exist.

Current-code contact evidence (2026-11-14): runs64/65/67/68/71 completed the full
recipe and passed independent trace evaluation, including fixture/repeat and
light-carton Home/repeat cases. Lift is explicitly measured at the uniform-
material model centre of mass; the asset corner is reported separately.
All pads were retained under load, offsets remained fixed, opening was measured
on support and final holds confirmed. Nominal Home run71 passed at0.5mm/s:
29.893mm COM lift and0.511mm maximum relative error. The default now uses this
slower profile. Nominal Home at1mm/s (run70) and0.4kg/friction0.8 (run69) were
rejected by the strict passive-finger speed limit; neither is qualified.
The nominal0.5mm/s repetition in run74 also stopped before its planned fault
injection at0.052335rad/s. Run71 is a positive individual result, not evidence
of repeatable nominal handling. The default remains an experimental simulation
profile with retained-grip aborts; nominal grasp robustness is still unresolved.
All three loaded runtime fault cases below passed. Earlier passes
remain historical evidence of their declared source/reference-point versions.
See [HANDOVER.md](../HANDOVER.md) for current run IDs, assumptions and limits.

| Run | Mass / friction | Start / object speed cap | COM lift | Maximum relative position error |
| --- | --- | --- | --- | --- |
|64|0.3kg /0.6|Pregrasp fixture /1mm/s|29.921mm|0.315mm|
|65|0.3kg /0.6|Repeat without reset /1mm/s|29.821mm|1.284mm|
|67|0.2kg /0.4|Home /1mm/s|29.809mm|1.424mm|
|68|0.2kg /0.4|Repeat without reset /1mm/s|29.813mm|1.581mm|
|71|0.3kg /0.6|Home /0.5mm/s|29.893mm|0.511mm|

These are tested pairs and start conditions, not a rectangular mass/friction
operating region. Run66 additionally aborted before contact on a200.368ms joint
reception gap. Its failure remains part of the record. The sealed workspace
artifact `setup/tasks/manipulation_qualification_20261114/result.json` references
the per-case source/scene/report hashes and separates positive, rejected and
fault-injection cases. The final status is `test_matrix_complete_with_limitations`,
with nominal grasp repeatability explicitly false. Earlier development runs
retain their original source bindings.
The1mm/s fixture also produced a passive-finger speed rejection in run73 before
its planned fault injection. Successful cases therefore do not establish
deterministic success even from that fixture. A pre-injection failure is never
a passed fault test. The completed runner/guard-loss tests75/77 use the explicit
0.2kg/friction0.4 Home profile at0.5mm/s. They cannot qualify nominal mass.

Asset poses, mesh coordinates and commanded object transforms retain the source
asset frame. `lift_reference_point_object_m` declares a separate verification
point at the same centre of mass used by the simulated inertial model. This
avoids coupling the lift metric to permitted small rotations about a corner.
The30mm±2mm lift criterion and2mm/1degree relative corridor remain unchanged;
no grasp offset, perception pose or trajectory is rewritten for the metric.

## Agent workflow

For subsequent agent tasks, load the repository skill
[`uwa-manipulate`](../.agents/skills/uwa-manipulate/SKILL.md). It routes to this
interface and current evidence without rediscovering the implementation.

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 run uwa_cell_tasks cell_task skills
ros2 run uwa_cell_tasks cell_task prepare --output setup/tasks/my-contact-scene
ros2 launch uwa_cell_tasks grasp.launch.py \
  scene:=$UWA_WS/setup/tasks/my-contact-scene
```

This launches a separate world `uwa_grasp_lab`, private ROS clock, TF tree and
controllers under `/uwa_grasp_validation`. The existing simulation is not
restarted. Do not launch a second grasp world while the first is alive. Both
worlds share this PC's compute resources; avoid concurrent CPU-heavy benchmarks.
The contact profile uses a1ms physics step and explicit real-time factor0.6
for compute headroom on this shared workstation. Wall-clock state freshness,
source-progress checks and independent watchdogs are unchanged. Accelerated
contact qualification is rejected by configuration validation.

After all nodes are ready and before starting a recipe, apply the measured
workstation CPU profile from another sourced terminal:

```bash
python3 src/multi_arm_manipulation_UWA/tools/configure_manipulation_cpu.py \
  --scene setup/tasks/my-contact-scene
```

This scopes descendants of that exact launch: physics CPUs0–3, guard CPU4,
supervisor CPU5. Camera/rendering policy and other launches remain untouched.
It writes a sealed `cpu-profile.json`; this is affinity, not a CPU reservation
or a real-time guarantee. It requires those CPUs on this16-core workstation.
Run recipes with `taskset -c 6-11 ros2 run ...` in the qualification profile.
Start the trace using `--prepare` before the runner, allow discovery to settle,
and verify its trace file exists before resetting/arming controllers. Starting
new ROS participants during an armed run has correlated with freshness faults.
Wait for measured stationary readiness before reset; a partial reset is a
failed start, not permission to proceed with the remaining held arms.

Clock, actual object pose and contact data are published directly from the
physics ECM into private ROS topics. The pose/contact timestamp explicitly
labels the completed previous physics result (one step old). No simulator
truth is supplied to the image pose estimator. The older `bridge` diagnostic
adapter and standalone clock bridge are not launched in this profile.

In another sourced terminal:

```bash
ros2 run uwa_cell_tasks cell_task run \
  --scene setup/tasks/my-contact-scene --output setup/tasks/my-grasp-run \
  --reference setup/tracking/models/carton_avocado_v1/reference.npz
ros2 run uwa_cell_tasks cell_task status setup/tasks/my-grasp-run
ros2 run uwa_cell_tasks cell_task preview setup/tasks/my-grasp-run
```

Run `run` in a persistent process while reviewing it from another terminal/tool.
At `WAITING_REVIEW`, read `review.json`, the native images and image overlays.
Assess strategy, whole-cell plan or pregrasp alignment as requested. Submit the
observed hash and the actual reason for the decision:

```bash
ros2 run uwa_cell_tasks cell_task review setup/tasks/my-grasp-run \
  --sha256 HASH_FROM_CURRENT_REVIEW --decision continue --reason 'Specific review findings'
```

`observe`/`replan` restart observation within the configured three-attempt limit;
`abort` latches the owned arms. Reviews time out after300s. The agent performs
these reviews itself within the user's task; a separate manual approval per
phase is not required. A decision from another revision is rejected.

```bash
ros2 run uwa_cell_tasks cell_task stop setup/tasks/my-grasp-run
```

`STOP REQUESTED` is not confirmed standstill. Read the resulting state and hold
confirmation. No automatic open, recovery or return motion occurs. A failed
run cannot be resumed with its old directory. The independent supervisor retains
holds after task loss. A physically held group cannot be reset automatically.

## Skill and data interfaces

`cell_task skills` returns versioned contracts, required evidence, resources,
timeouts and stop behavior. Public Python modules separate `core` (contracts,
reviews, `GraspGroup`), `scene` (asset/contact shapes), `planning` (grasp proposals,
approach and shared object motion), `observation` (image worker), `runtime`
(simulation actions) and `guard` (independent runtime verification). The first
recipe composes these functions; new manipulation recipes reuse their interfaces.

| Skill | Python entry point / composition | Required result |
| --- | --- | --- |
| `observe` | `observation.observe` | Fresh image-only `VALID` pose and inspection images |
| `propose_grasp` | `planning.grasp_candidates` | Ranked candidates with explicit assumptions and pad envelope |
| `plan_approach` | `plan_approach`, `grasp_entry`, predicted `object_trajectory` | Bound, collision-checked approach/entry/lift witness |
| `review` | `runtime.await_review`, `RunStore.submit_review` or CLI `review` | Current packet hash, revision and concrete decision reason |
| `approach` | `Simulation.follow(plan['trajectory'])` | Measured checked endpoint and standstill |
| `inspect_pregrasp` | `observe`, pose comparison and alignment review | Fresh image alignment within corridor |
| `grasp` | `grasp_entry`, `Simulation.follow`, `Simulation.grippers(.8)` | Stable two-sided contact at both grippers |
| `form_group` | `core.GraspGroup`, publish immutable group record | Frozen object-to-TCP offsets, independently monitored membership |
| `move_object` | `planning.object_trajectory`, `Simulation.follow` | One object path and shared twelve-joint time law |
| `set_down` | Same object-path compiler toward support | Actual supported object, stationary carrying arms |
| `release` | `grippers(0)`, `GraspGroup.release`, guard acknowledgement, `stop` | Open grippers, dissolved group, confirmed resource holds |

The recipe in `runtime._run_task` shows the complete ownership, review and
cleanup composition. These functions are not independent unguarded robot APIs:
reuse the resource lease, scene binding, heartbeat and retained-grip stop path.
The predicted lift witness cannot form a loaded group; actual contacts and
fresh visual/actual-TCP capture are required first.

- All transforms are right-handed4×4 matrices, metres, +Zup. Twists are
  `[vx,vy,vz,wx,wy,wz]` at the object origin in the common world frame.
- `scene.json` binds geometry/configuration; approach plans bind the complete
  measured start, object geometry, model and selected grasp. JSON artifacts
  carry a SHA256 over canonical contents.
  The scene also pins task Python sources, the cooperative geometry module,
  launch file, contact plugin and native clock executable. Source changes
  require a newly prepared/relaunched scene; the runner checks bindings during
  execution. Edit task code between runs, not while a bound run is active.
- Observation is `uwa_cell_tracking` image registration with matching rendered
  CameraInfo. The contact simulator has no image sensors. A separate static
  photo world contains measured joint poses, the physical simulated object's
  visual, and cameras; it has no controllers, collision bodies or motion plugins.
  Physical and renderer timestamps remain separately labelled. Arms and object
  are audited stationary during capture; image estimation is another process.
  Simulator truth defines the rendered scene and evaluates motion, but is never
  passed to the image estimator as an object-pose prior or hypothesis selector.
- Noiseless frames can have identical pixels. Only this simulator adapter accepts
  them with advancing renderer timestamps; it registers once and does not count
  repeated pixels as independent measurement information. Physical camera checks
  in `uwa_cell_tracking` remain unchanged.
- Run outputs include strategy, rejected candidates, plan, image inspections,
  reviews, captured group offsets and object-derived actuator samples. A fresh
  visual check precedes execution after plan review.

## Rigid grasp group

After both grippers establish two-sided contact, capture and freeze
`T_object_tcp` from the visual object pose and actual TCPs. Geometry is shared
with `match_cooperative_handling.rigid_object`, which implements the same rigid
object-to-TCP and rotational lever-arm principle as that repository's follower.

`T_world_tcp_i = T_world_object · T_object_tcp_i`

After grasp there is one object path and one common time law. Continuous IK
derives the actuator samples; it does not plan independent arm trajectories.
A single twelve-joint `rigid_object_controller` executes the entire group.
The most restrictive joint scales the whole time law. Dense interpolated FK
and collision checks verify the compiled path. Other arms remain measured scene
obstacles. No independent member command is exposed by `GraspGroup`.

The independent geometric process includes measured finger joints, observes
contact loss/rigidity, and expands member faults to both carrying arms. The
existing independent resource supervisor handles guard loss and pair leases.
The gripper target latch is separate from arm holds: arm stopping cannot open
the fingers or discard the retained squeezing target. No relative-pose update
is accepted while the group remains loaded.

For a compact read-only agent packet (after sourcing the environment):

```bash
python3 src/multi_arm_manipulation_UWA/tools/inspect_manipulation_review.py setup/tasks/my-grasp-run
```

It verifies packet hashes and reports pending status, image paths, candidate
assumptions, alignment error and trajectory bounds. It does not approve anything;
actual images and current task/guard evidence remain part of the agent review.

## Contact model and limits

The original visual-only carton and ordinary cell launch remain available.
The opt-in scene extrudes the asset's outer skin triangles into convex thin
prisms, preserving the open interior and observed upper cutouts. A vertical
envelope decomposition preserves each wall's area/contour and makes its lower
contact face one analytic box. It rejects internal holes rather than filling
them. The current carton has40 parts; an independent120701-point occupancy
comparison per wall found no change from the earlier triangulation. It computes
mass properties from those volumes and uses real gravity/contact. No attachment
joint or pose teleportation is used for grasping or lifting.

The current experimental default selects the pinned DART engine and energy-
balanced elastic gear couplings: each passive reaction is applied equally to
its driver in generalized coordinates. A native test checks zero aligned torque,
reaction/work balance, bounded coupling and dissipative damping. Gear stiffness
100Nm/rad, motor stiffness10Nm/rad and joint damping0.08Nm·s/rad are unmeasured
assumptions. Previous softer3/10Nm/rad models closed stably but failed pickup.
The revised100Nm/rad profile uses gravity-aligned wall pinches. The current
source-bound qualification cases and limits are listed above and in HANDOVER.

Each gripper has one PD motor, bounded to0.35Nm at each1ms physics step. Actual
finger positions/velocities enter planning and the independent guard. Motor effort
is applied actuator torque, not an inferred contact force. No robot/object
attachment or passive-joint pose reset is used by the right contact backend.
The mechanism approximates a parallel transmission and does not validate the
adaptive Robotiq mechanism or real cardboard holding strength.

An optional native internal gear profile uses Bullet Featherstone. DART here
lacks that feature, so incompatible configurations are rejected. This comparison
profile matched ratios at rest but became numerically unstable during free
closure; it is unqualified and is not the default. Its physical spawn model has
one fixed anchor to retain all cell geometry and unchanged world/tool poses.
Engine binary, world/carton SDFs, source and contact backend are SHA-bound.
See [Gazebo's native mimic feature](https://gazebosim.org/libs/physics/) and
[explicit engine selection](https://gazebosim.org/api/sim/10/physics.html).
Right fingertip contact geometry uses conservative analytic housing/pad boxes,
constructed from clipped source-mesh bounds with the original inner contact
plane. Detailed visuals remain. Fixed pad links inherit the original internal
four-bar hinge adjacency exception; no environment/interarm exception is added.
Only pads may intentionally touch the carton; housings remain collision-checked.
The triangle-surface coverage and initial full-scene clearance are tested.
The first wall-pinch strategy assumes an upright empty carton on horizontal
support. Closing axes use image-derived yaw projected onto the gravity plane,
avoiding small planar PnP roll/pitch errors in a vertical-wall pinch. Image tilt
above2degrees is rejected. This is an explicit strategy assumption, not a
ground-truth pose prior or a general tilted-object grasp.

Candidate insertion depth accounts for the complete pad boxes and finger FK
over nominal closure0.76–0.8rad, with their highest point3mm below the continuous
wall surface. The finite envelope is a planning check; actual finger states and
contacts still need the independent runtime checks.
The two right arm position actuators also use measured physics-step state,
bounded to0.05rad/s and0.5rad/s². They execute the combined trajectory; they
do not generate separate paths. The stock backend's cached position produced
short impulses during this contact experiment. This optional actuator model is
still idealized and does not establish real UR force or tracking performance.
The common controller supplies position and velocity references; the actuator
predicts that reference between ROS samples. Switching to position-only hold
resources disables velocity feedforward. Gazebo's consumed velocity command is
recreated every physics step. A5mrad action path tolerance detects failed tracking.

The task guard independently latches every received right-joint speed above
0.05rad/s plus1e-8 numerical tolerance. Peaks persist across subsequent quiet
samples and10Hz geometry ticks; the general guard's5% tolerance is not used as
the task envelope. Joint telemetry is100Hz: this is sampled evidence, not a
continuous-time velocity guarantee.

Opening requires both the action result and all12 measured finger DOFs within
0.02rad of open and below0.003rad/s for0.3simulation seconds. A successful
action with physically closed fingers is rejected. The0.5-damping comparison
exposed this case and was rejected in the agent image checkpoint before entry.

Only the read-only ListControllers query is retried once after a missing reply.
Reset, switches, captures and grip-latch mutations are not replayed. Stop sends
requests to both members before waiting; one transport failure cannot prevent
the other request. Confirmation requires fresh measured states and active
independent hold controllers. A service acknowledgement alone is not a hold.

Defaults in `config/carton.yaml`: mass0.3kg, friction0.6 and thickness2.5mm are
unmeasured simulation assumptions. Rigid cardboard cannot establish crushing
strength or real holding reliability. Native real-camera calibration and the
preliminary physical world anchors are not improved by this simulation.
Grasp ranking includes reach, the mass model's centre of mass, horizontal
support-line offset and an approximate static vertical load split. This estimate
does not prove frictional holding or cardboard strength.
The default object speed cap is0.5mm/s. The earlier fixture/repeat and light
Home cases, and the loaded-fault fixtures, use explicitly bound1mm/s profiles;
their results do not establish nominal Home operation at1mm/s. Closure advances at
0.02rad/s in free space and0.004rad/s from0.65rad into contact; opening uses
the coarse rate. The native force servo enforces the same reference limits.

Continuous clock/object/contact streams use latest-state best-effort delivery;
slow image receivers cannot request a reliable backlog on the physics publisher.
Wall-clock freshness checks and retained-grip stops remain unchanged. A separate
lease-owned observation stress tool runs full image localization without arm or
gripper trajectory goals; scene reset/rearm and final resource holds are explicit.
Current transport test: twelve `VALID` observations, no guard faults, measured
maximum source-advance gap124.5ms (150ms joint freshness limit). This is an
observed test result, not a hard real-time guarantee.

```bash
python3 src/multi_arm_manipulation_UWA/tools/stress_manipulation_observation.py \
  --scene setup/tasks/my-contact-scene \
  --reference setup/tracking/models/carton_avocado_v1/reference.npz \
  --output setup/tasks/my-observation-stress --captures 12
```

Before starting the runner, start a separate read-only evaluation trace in
a persistent process. `--prepare` requires a new run directory and creates its
CREATED state; the runner later uses that same directory:

```bash
python3 src/multi_arm_manipulation_UWA/tools/trace_manipulation.py setup/tasks/my-grasp-run --prepare
```

The JSONL records contact/support, measured joints, simulator object pose and
holds. It is an evaluation artifact and is never supplied to the planner.

```bash
python3 src/multi_arm_manipulation_UWA/tools/validate_manipulation.py \
  --scene setup/tasks/my-contact-scene setup/tasks/my-grasp-run
```

This writes `validation-report.json`, distinguishing a complete supported lift
from a planned witness or a contact-only stop. Rechecking an old development run
does not silently qualify it against changed implementation binaries.

The visual object estimate fixes the control offsets. A separately frozen
simulator-truth baseline measures mechanical slip from the instant of confirmed
grasp; constant perception error is not mislabelled as subsequent slip. That
evaluation baseline is never supplied to planning or control, and neither set
of offsets is updated while carrying the object.

Five complete physical-contact lifts, mass/friction variations and fault tests
are the intended acceptance. Only actually completed tests in HANDOVER count
as evidence; merely having these commands is not a successful grasp result.

RViz must use the private TF topics `/uwa_grasp_validation/tf` and `tf_static`,
the private robot description, and `/uwa_grasp_validation/tasks/markers`.
The marker labels simulator truth explicitly and displays group/stop state in text.

## Loaded-group fault verification

`tools/test_manipulation_fault.py` deliberately fails a running isolated recipe.
Start its probe before pickup, while the agent still reviews the recipe. It waits
for a fresh, confirmed two-arm group with all four contacts, unsupported object
and at least5mm actual lift, then injects one selected fault. `member_stop` calls
the scoped front-member stop service; `runner_pause` or `guard_pause` pauses only
the exact matching task process. The process is always continued for cleanup;
the stopped recipe is never resumed. These are simulation tests only.

The report requires both independent holds, stationary arms for a retained
window, fresh telemetry, retained pads, unsupported load and the rigid corridor,
then a FAILED recipe with confirmed holds. No gripper-open or trajectory command
is sent. A loaded failed group cannot be reset as a new task; retain its evidence
and deliberately end the own test world before another isolated test episode.

```bash
python3 src/multi_arm_manipulation_UWA/tools/test_manipulation_fault.py RUN \
  --scene SCENE --fault runner_pause
```

A passed fault test is a negative-case verification, never a completed grasp run.

Loaded fault evidence (2026-11-14), all with four retained pads, unsupported
load, fresh actual telemetry, retained stationary holds and an expected FAILED
recipe with confirmed stop:

| Run | Fault | Mass / friction / object cap / start | Max relative position error | Hold confirmation including stationary window |
| --- | --- | --- | --- | --- |
|72|One member stopped|0.3kg /0.6 /1mm/s /pregrasp fixture|0.271mm|0.394s|
|75|Runner paused|0.2kg /0.4 /0.5mm/s /Home|1.421mm|0.920s|
|77|Guard paused|0.2kg /0.4 /0.5mm/s /Home|1.419mm|0.617s|

These times include the measured stationary confirmation window; they are not
raw controller reaction times or a worst-case stopping guarantee. The probe
checks a healthy pre-injection guard and freezes its mechanical baseline while
the group is still supported. The independent trace audit also checks that no
right-member holds or faults preceded injection. The physical-stop deadline is
5wall-seconds; the900s wait budget only covers reaching the eligible load state.

Rejected attempts73/74 never reached injection. Attempt76 failed before motion
because an unselected left passive finger did not settle; the right pair held,
the carton remained supported and no fault was injected. A fresh world was used
for77. Every failed attempt is retained. Test worlds were explicitly ended after
confirmed holds, without opening or resuming a loaded group. The ordinary cell
simulation and physical robots were untouched.
