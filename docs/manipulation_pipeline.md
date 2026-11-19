# Object-led manipulation skills (simulation)

The first recipe is `avocado_carton`, `right_front` + `right_rear`, empty rigid
carton, 30 mm lift, two-second dwell, set down and release. The task transport
cannot address hardware. It requires domain64, `uwa_cell_sim`, LOCALHOST and an
isolated `/uwa_grasp_*` namespace. No real power, brake or program commands exist.

**Current Gazebo workflow, 19 November 2026.** Inspect collision geometry,
joint bounds, timing and rigid-grasp/tool constraints in the compiled plans.
Gazebo plays those plans using its contact physics and normal action controllers.
Pad contact triggers the simulated grip latch. The runtime does not supervise
joint speeds, passive joints, collision clearance, slip or standstill.
The experiments listed below retain their original implementation and results.

See the historical [500g force/speed/stop report](carton_dynamic_validation_2026-11-16.md)
for current measured results, profile differences and remaining limits.

The [matched 1×/5× vertical-lift comparison](carton_speed_comparison_2026-11-17.md)
records a completed 147.8 mm lift/return at fivefold carrying speed. Exploratory
`carrying_speed_multiplier` (1–5) compresses the complete shared object law;
`force_comparison_lift` selects this longer translation witness without rolling.
Explicit `joint_velocity_overrides_rad_s` remain bound to individual right-arm
joints and their full stopping budgets. No limit is automatically relaxed.
The complete 90° roll remains unqualified at 5×.

## Exploration objective (clarified2026-11-16)

Use contact simulation to explore fast task execution and find the limiting
conditions. Vary path speed, acceleration and jerk by phase; compare cycle time,
collisions, contact forces/impulses, actuator loads, slip and internal loading
of the rigid grasp group. Carrying arms retain one object path and shared time
law. Repeat across mass, friction and pose variations, retaining failed cases.
The intended hardware trajectory then includes allowance for model uncertainty
and is checked against real measurements. A fixed percentage below a simulated
maximum alone is not evidence of safe physical execution.

The existing slow settings below are commissioning profiles, not measured robot
performance limits. Higher-speed experiments need separate bound profiles and
new evidence. Faster replay does not change forces in the original physics.

Native force observation now records deduplicated contact loads, impulse,
physics-step peaks,10ms means and shoulder/wrist joint reactions in joint frames.
The12-case known-load matrix (0.3/0.6kg,1/0.5/0.25ms, two repeats) passes static,
dynamic-balance, joint-frame and impact-impulse checks. Impulse spread is0.1574%;
rigid impact peaks scale inversely with step size. Never equate these peaks with
cardboard failure. Raw body1/2 attribution is unreliable after Gazebo collision
reordering; contact load magnitudes are unsigned. Native link velocity and
acceleration can remain latched after rest; independent position-based checks
were required. Evidence: `setup/tasks/force_reference_20261116_matrix01/`.

A500g idle-cell integration also passes:4.904986N support force versus4.905N,
all four selected joint reactions, no invalid wrench or missing force window.
Arm actuators and rigid cardboard remain idealized. These checks establish the
measuring path in this engine, not real UR dynamics or carton crushing.

`config/carton_exploration.yaml` explicitly enables experimental envelopes.
Arm and finger velocity limits are separate; unselected left arms retain0.05rad/s.
Plan checks include per-joint limits and modeled braking/latency reserves. The minimum grasp-entry duration is
configurable and entry uses a checked C2 spline with one common quintic law.
Object carrying always retains its single object path and common time law.
A configured envelope can be rejected before any movement if its reserve does
not fit the start geometry. An optional arm `joint_jerk_rad_s3` uniformly retimes the complete approach, entry
and object motion using exact extrema of the controller’s quintic segments.
This bounds planned command jerk, not measured servo jerk or stop behavior.
Three loaded stop cases now pass for the explicit10mm/s/0.2rad/s-finger
profile below. A physical maximum remains unmeasured. Failed attempts remain
evidence.

For a separate load study, `tools/trace_manipulation.py RUN --prepare` records
full received native force windows in `force-trace.jsonl` as well as the20Hz
motion trace. Analyze with `tools/analyze_manipulation_loads.py RUN --scene SCENE
--output NEW_REPORT.json`. Its complete-coverage flag requires valid consecutive
force windows;20Hz legacy snapshots cannot establish complete force coverage.
Loads are summed across all pairs on each jaw. The sum of pair peaks is a
conservative upper bound because individual peaks may not coincide.

### Finite experiment ladder

`tools/explore_manipulation.py --config PROFILE --reference REFERENCE_NPZ
--output NEW_DIRECTORY --object-speeds 0.005 0.01 --repeats 2` prepares and
launches separate cases, starts optional experiment recording, configures its
physics process, waits for agent reviews, evaluates load traces after playback
and ends its own world. It refuses another active grasp
launch. Each case keeps profile, logs and raw evidence. No automatic image or
plan approval is supplied. The result lists observed cases without assuming a
monotonic speed boundary. A comparison of10ms pad means with the user’s50N
reference is explicitly separate from peak forces and material damage.
The first two-case ladder completed at5/10mm/s: both carried500g to29.4mm
and stopped on passive finger-speed bounds during descent. Both full force
traces are gap-free and below the user load reference. No complete fast500g
cycle was qualified by that initial soft-preload profile. `physics_step_s` supports
explicit0.1–1ms refinement. The0.5ms comparison also stopped on the configured
passive-finger bound during initial load transfer; convergence is unproven.

For isolated contact experiments `tools/prepare_manipulation_fixture.py --scene
SCENE --run RUN --output NEW_FIXTURE` derives a new initial pregrasp layout from
a verified plan. It verifies unchanged collision geometry/kinematics. Pass its
`layout.yaml` with `explore_manipulation.py --layout`. It changes no existing
world and provides no Home-approach qualification. The current contact-dynamics
candidate increases the finger observation bound while reducing the arm bound
so the complete stopping reserve still fits; no guard check is disabled.

The stronger virtual motor preload subsequently passed a full5mm/s fixture
cycle and **two complete10mm/s Home cycles** with500g. The Home repeats measured
29.924mm COM lift,0.274mm maximum relative position error and5.556N maximum
per-jaw peak upper bound. Both full force traces are gap-free; all pads remain
under load until supported release, and final holds are confirmed. No real
force-setting calibration or maximum physical speed follows from these cases.
Evidence: `setup/tasks/carton_preload_home_20261116_01/` (finger bound0.15rad/s).
The separate `carton_preload_faults_20261116_03/` passes all three loaded
member/runner/guard stop tests at10mm/s with finger bound0.2rad/s and its larger
full stopping reserve. All four pads remain engaged, relative error<=0.240mm,
gap-free per-jaw peak upper bounds<=5.394N; implementation binding and scoped
cleanup pass. Two complete Home repeats with exactly this0.2rad/s profile now
also pass (`carton_preload_home_20261116_02/`):29.924mm lift, relative error
<=0.274mm, gap-free per-jaw peak upper bounds<=5.504N. All five cases use the
same bound implementation and profile; their sealed index and exact profile are
in `setup/tasks/manipulation_qualification_20261116/`. The earlier0.15rad/s Home
results retain their original profile.

These last tests use the immutable baseline under
`setup/tasks/carton_frozen_baseline_20261116_01/` to preserve concurrent carton-
rotation development. Source the normal cell environment, then that snapshot's
`environment.bash` to reproduce its implementation; file hashes and copied
tools are retained there. This does not qualify the separate rotation recipe.
For a new fast translation task, use the index's explicit `qualified-profile.yaml`
and frozen environment as shown in the compact report; the package default
remains the historical slow commissioning profile.

`cell_task skills` now lists16contracts including force reference validation,
load observation, virtual fixture preparation, experiment cases and loaded-stop
tests. New scenes also bind local planning/playback dependencies, the shared
motion configuration, native hold library and RRT worker (`binding_scope v2`).
Older sealed reports retain their original, narrower dependency binding.

### Force sensing first; compliant mount as fallback

User preference2026-11-16: first validate direct force reporting. Only if it
proves unsuitable, test a UR base on a passive spring/damper linear stage and
infer a force component from displacement. Do not add that stage by default.

Installed interfaces include contact wrench fields, the Gazebo ForceTorque
system and JointTransmittedWrench. The pinned DART9.5.2 binary exposes contact
reporting, transmitted joint wrench, spring stiffness and spring reference
features. This is capability evidence, not measured accuracy. References:
[contact-force API](https://gazebosim.org/api/physics/9/GetContacts_8hh_source.html),
[joint F/T sensor](https://gazebosim.org/api/sensors/9/classgz_1_1sensors_1_1ForceTorqueSensor.html),
[spring/damper schema](https://raw.githubusercontent.com/gazebosim/sdformat/sdf16/sdf/1.12/joint.sdf).

First compare known static load and lever arm, dynamic force balance, repeated
runs and smaller physics steps. Check force frames/signs and avoid counting
the same contact from multiple sensors twice. Evaluate impulse and defined
time-window force averages alongside rigid-contact solver peaks.

A passive spring reference provides restoring action conceptually; an active
axis is not inherently required. Quasistatically, its axial force is approximately
stiffness times displacement from the reference. Dynamic inference must account
for damping, inertia and robot self-motion/loading. A single stage observes one
direction. Excessive stiffness may worsen numerical conditioning. The displaced
base must enter actual world-to-TCP kinematics without rewriting grasp offsets.
The mount changes dynamics and uses the same physics solver, so it is not an
independent guarantee of correct contact mechanics. No stage has been implemented: the direct measurement path passed the
reference checks above and currently makes that fallback unnecessary.

## Existing commissioning evidence

Current input update2026-11-16: the user reports an empty-carton mass of0.5kg
and comfortable50N loading at one jaw/wall contact patch. The default mass is
updated accordingly;50N is an exploratory comparison reference, not a measured
failure limit. Force observation is enabled for newly prepared scenes.
The older cases below used their own declared mass/source versions and do not
qualify the new0.5kg profile or the new observer.

Historical commissioning evidence (2026-11-14): runs64/65/67/68/71 completed the full
recipe and passed independent trace evaluation, including fixture/repeat and
light-carton Home/repeat cases. Lift is explicitly measured at the uniform-
material model centre of mass; the asset corner is reported separately.
All pads were retained under load, offsets remained fixed, opening was measured
on support and final holds confirmed. Nominal Home run71 passed at0.5mm/s:
29.893mm COM lift and0.511mm maximum relative error. The default retains that
slow speed but uses the new mass above. Nominal Home at1mm/s (run70) and0.4kg/friction0.8 (run69) were
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

### Watch the recorded successful cycle

For a visual demonstration, replay the measured joints and carton poses of
qualified run71 in a separate RViz window. This is a labelled recording,
not a new contact simulation or a new validation result. The private
`/uwa_grasp_replay` topics are display-only; no controllers or robot commands
are started. The original trace and models are checked against their stored
qualification hashes. The source files and other simulations stay unchanged.

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
python3 src/multi_arm_manipulation_UWA/tools/replay_manipulation.py \
  --run setup/tasks/carton_grasp_run71 \
  --scene setup/tasks/carton_contact_20261114_v95 \
  --qualification setup/tasks/manipulation_qualification_20261114/result.json \
  --output setup/tasks/my-carton-replay --speed 8
```

Use a new output directory. Click **Play replay**; **Pause**, the speed selector
and timeline control playback. **Restart**, then **Play replay**, shows it again.
The complete recording takes about two minutes at8×. The high-contrast control
window labels the recorded phase, actual COM lift, four pad contacts and table
support. **Close replay** also closes only its own RViz/state-publisher children.
The player uses host Qt6 and clears inherited Snap GTK paths for this process.

### Run a fresh contact simulation

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

To prepare the house/drawing demo at the current Gazebo speed, pass its
saved drawing reference directly:

```bash
ros2 run uwa_cell_tasks cell_task prepare \
  --drawing-recipe /absolute/path/to/drawing-recipe.json \
  --layout /absolute/path/to/layout.yaml \
  --output setup/tasks/my-drawing-scene
```

This selects `config/carton_drawing_fast.yaml` with a 1 rad/s arm-joint cap
and a real-time factor target of 1. The planner uses a shared time law up
to the acceleration and jerk limits of the profile. An explicit
`--config` selects another profile, including historical reproduction.
Launch and run this scene with the same layout. Additional watchers or tests
require the user's explicit consent.

This launches a separate world `uwa_grasp_lab`, private ROS clock, TF tree and
controllers under `/uwa_grasp_validation`. The existing simulation is not
restarted. Do not launch a second grasp world while the first is alive. Both
worlds share this PC's compute resources; avoid concurrent CPU-heavy benchmarks.
The fast drawing profile uses a 1 ms physics step and targets real-time
playback. The achieved factor depends on the contact solver and host load.

After all nodes are ready and before starting a recipe, apply the measured
workstation CPU profile from another sourced terminal:

```bash
python3 src/multi_arm_manipulation_UWA/tools/configure_manipulation_cpu.py \
  --scene setup/tasks/my-contact-scene
```

The optional affinity helper assigns CPUs 0–3 to that launch’s physics
process and writes `cpu-profile.json`.

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
`abort` ends the recipe. Reviews time out after300s. The agent performs
these reviews itself within the user's task; a separate manual approval per
phase is not required. A decision from another revision is rejected.

```bash
ros2 run uwa_cell_tasks cell_task stop setup/tasks/my-grasp-run
```

`STOP REQUESTED` asks the runner to cancel its current goals. The run state
records the cancellation responses. The simulated grip latch remains until the
release phase or an explicit intervention.

## Skill and data interfaces

`cell_task skills` returns versioned contracts, required evidence, resources,
timeouts and stop behavior. Public Python modules separate `core` (contracts,
reviews, `GraspGroup`), `scene` (asset/contact shapes), `planning` (grasp proposals,
approach and shared object motion), `observation` (image worker), `runtime`
(Gazebo playback). The first
recipe composes these functions; new manipulation recipes reuse their interfaces.

| Skill | Python entry point / composition | Required result |
| --- | --- | --- |
| `observe` | `observation.observe` | Fresh image-only `VALID` pose and inspection images |
| `propose_grasp` | `planning.grasp_candidates` | Ranked candidates with explicit assumptions and pad envelope |
| `plan_approach` | `plan_approach`, `grasp_entry`, predicted `object_trajectory` | Bound, collision-checked approach/entry/lift witness |
| `review` | `runtime.await_review`, `RunStore.submit_review` or CLI `review` | Current packet hash, revision and concrete decision reason |
| `approach` | `Simulation.follow(plan['trajectory'])` | Trajectory action completion |
| `inspect_pregrasp` | `observe`, pose comparison and alignment review | Fresh image alignment within corridor |
| `grasp` | `grasp_entry`, `Simulation.follow`, `Simulation.grippers(.8)` | Stable two-sided contact at both grippers |
| `form_group` | `core.GraspGroup`, publish immutable group record | Frozen object-to-TCP offsets |
| `move_object` | `planning.object_trajectory`, `Simulation.follow` | One object path and shared twelve-joint time law |
| `set_down` | Same object-path compiler toward support | Completion of the planned set-down action |
| `release` | `grippers(0)`, `GraspGroup.release` | Opening trajectory and dissolved group |

The recipe in `runtime._run_task` shows the complete ownership, review and
cleanup composition. Reuse the resource lease, scene binding and explicit
trajectory actions.
The predicted lift witness cannot form a loaded group; actual contacts and
fresh visual/actual-TCP capture are required first.

- All transforms are right-handed4×4 matrices, metres, +Zup. Twists are
  `[vx,vy,vz,wx,wy,wz]` at the object origin in the common world frame.
- `scene.json` binds geometry/configuration; approach plans bind the complete
  measured start, object geometry, model and selected grasp. JSON artifacts
  carry a SHA256 over canonical contents.
  The scene also pins task Python sources, the cooperative geometry module,
  launch file, contact plugin and native clock executable. Source changes
  require a freshly prepared scene. The runner verifies scene and plan
  bindings before playback.
- Observation is `uwa_cell_tracking` image registration with matching rendered
  CameraInfo. The contact simulator has no image sensors. A separate static
  photo world contains measured joint poses, the physical simulated object's
  visual, and cameras; it has no controllers, collision bodies or motion plugins.
  Physical and renderer timestamps remain separately labelled. Image
  estimation runs in a separate process.
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

The gripper latch maintains the squeezing target in the contact model.
The group keeps its original transforms for all phases of the compiled plan.

For a compact read-only agent packet (after sourcing the environment):

```bash
python3 src/multi_arm_manipulation_UWA/tools/inspect_manipulation_review.py setup/tasks/my-grasp-run
```

It verifies packet hashes and reports pending status, image paths, candidate
assumptions, alignment error and trajectory bounds. It does not approve anything;
actual images and the current artifacts remain part of the agent review.

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
recreated every physics step. Both arm and gripper actions use the plan’s time law. The action result marks
completion of the open command. During closure, contact engages the latch.

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

Clock, object and contact data use best-effort delivery. Recording is optional
for experiments that need post-run load or contact data.

Before starting the runner, start a separate read-only evaluation trace in
a persistent process. `--prepare` requires a new run directory and creates its
CREATED state; the runner later uses that same directory:

```bash
python3 src/multi_arm_manipulation_UWA/tools/trace_manipulation.py setup/tasks/my-grasp-run --prepare
```

The JSONL records contact/support, measured joints, simulator object pose and
group membership. It is a record for post-run evaluation.

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

RViz must use the private TF topics `/uwa_grasp_validation/tf` and `tf_static`,
the private robot description, and `/uwa_grasp_validation/tasks/markers`.
The marker labels simulator truth explicitly and displays group/stop state in text.

## Historical loaded-group experiments

Earlier stop experiments are indexed in `setup/tasks/manipulation_qualification_20261116/`.
The Gazebo fault-injection tools were retired on 19 November.

### Gripper preload is part of the experimental model

The low-force contact-dynamics case stopped on2mm relative TCP/object error
after allowing larger passive-finger motion. This can include compliance as
well as slip. Increase of an observation bound alone does not establish holding
quality. `gripper_motor_torque_limit_nm` now controls only the virtual motor;
the elastic transmission retains its separate0.35Nm limit. Defaults remain
0.35Nm motor/10Nm/rad feedback. The explicit preload candidate tests0.7Nm motor
and30Nm/rad feedback, with measured pad loads deciding the comparison. These
are model parameters, not calibrated hardware force settings.

Robotiq lists20–235N Grasp Force for2F-85 in its
[manufacturer specifications](https://assets.robotiq.com/website-assets/support_documents/document/online/2F-85_2F-140_Instruction_Manual_Gen_HTML_20190524.zip/2F-85_2F-140_Instruction_Manual_Gen_HTML/Content/6.%20Specifications.htm).
That device-level specification is not automatically the force on one carton
wall patch; a real setting-to-contact-force calibration remains necessary.

## Experimental longitudinal quarter turn (2026-11-16)

`config/carton_roll_90.yaml` opts into lifting, a 90-degree roll about the
carton's longer horizontal asset axis, and placement on a side wall. The sign
faces the opening toward the scene-bound OAK optical pose. The material-model
centre of mass is the fixed rotation pivot. Geometry determines the required
clearance lift (about146mm in the current nominal scene); the old30mm lift
cannot clear this rotation. The carton starts across the table gap; the final
footprint is shifted wholly onto one horizontal table. The current experimental
profile selects the left table; the direct right-table descent has a checked
front-arm forearm/wrist collision. The arm speed cap is0.04rad/s to retain the
full stopping reserve; offline collision thresholds retain their documented values.

This reuses the same grasp proposals, approach planner, `GraspGroup`, immutable
offsets, common12-joint object-path compiler, supervisor and contact/slip guard.
Before entry the review includes a complete geometric carrying-path witness.
After real contact the full recipe is compiled again with measured TCP offsets
before pickup. All carrying motions keep a common time law. Opening requires
support and the measured sideways orientation; final orientation is checked
again after release. `object-targets.json`, `object-recipe.json` and
`object-turn.json` retain explicit evidence. The trace validator additionally
requires the unsupported turn and supported sideways release.

This is experimental software, **not a qualified contact cycle**. The first
offline nominal path can lift and turn geometrically, but its direct descent
encounters a front-arm forearm/wrist self-collision. Other original candidates
also fail collision, reach or stopping-reserve checks. A left-table alternative passes the complete dense geometry/timing check
(scene03). Its original global derivative bound makes the turn very slow; an
interval-wise conservative timing bound passes in scene04 (55.76s lift,
250.94s turn,61.88s descent). Contact evidence remains separate. The first Home
contact attempt was rejected before motion; the fixture attempt reached all
four pads but stopped before lifting on a170ms state gap. The RTF0.4 repeat lifts147.7mm but stops
near9degrees at2.03mm relative error. A model-COM-height pinch collides with
the palms and was rejected before contact. The stronger virtual preload trial also stopped before pickup on a169ms
state gap. All four cases retain their raw evidence and confirmed holds; no
physical quarter-turn pass is claimed. The sealed summary is
`$UWA_WS/setup/tasks/carton_roll_summary_20261116/result.json`. Consult work/carton-roll-90.md for current
results. Do not execute by bypassing collision checks. Earlier translation-only
passes do not qualify this recipe. No second grasp world may run concurrently.


Prepare this optional recipe with the existing interface:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 run uwa_cell_tasks cell_task prepare \
  --config src/multi_arm_manipulation_UWA/uwa_cell_tasks/config/carton_roll_90.yaml \
  --output setup/tasks/my-quarter-turn-scene
```

Use the existing isolated launch/recorder/review workflow above after confirming
there is no other active grasp world. `cell_task plan` also includes the complete
carrying-path witness for this profile; the default recipe stays translation-only.
The optional file-only preview tool consumes a sealed offline preflight packet:

```bash
python3 src/multi_arm_manipulation_UWA/tools/preview_carton_motion.py \
  --scene SCENE --plan PREFLIGHT.json --output NEW_PREVIEW.html
```

Play/pause, timeline, orbit and zoom are display-only. This animation represents
commanded model geometry, never successful contact physics. The regular
`cell_task preview RUN` shows the actual review and complete motion stages.

## Offline stopping-reserve model

`simulation_stop_reserve_mode: enforce` includes modeled stopping reserve in
plan verification. The explicit exploratory `observe` mode permits a plan
based on geometric clearance and the model margin, while retaining the modeled
reserve in planning evidence. Neither mode installs a runtime watcher.
