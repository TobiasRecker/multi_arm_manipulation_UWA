---
name: uwa-manipulate
description: Compose and review object-led manipulation tasks in the UWA digital robot cell, including two-arm carton grasps and rigid cooperative handling. Uses the simulation harness and explicit supported hardware staging; loaded hardware object motion is not implemented.
---

Read the repository AGENTS.md and current manipulation section in HANDOVER.md.
Latest real state19November overrides the historical18November state below:
both right grippers have confirmed OBJ2 contact on the supported carton at
FOR0/SPE16. Corrected high approach and open entry passed on hardware. During
closing the existing RR standstill monitor stopped its native program, so the
complete grasp run did NOT pass final validation. All four holds/standstill
were subsequently confirmed. Keep the contact members as a rigid HOLD-only
group: no independent trajectories, reset/play/opening or service migration
as automatic recovery. Current virtual-object/TCP references and raw state:
setup/tasks/carton_grasp_20261119/grasp/final-held-state.json. No lift occurred.
Read current HANDOVER before commands. Contact membership must be persisted
before a final native-readiness check that may fail.

Use [the task interface](../../../docs/manipulation_pipeline.md) and
`ros2 run uwa_cell_tasks cell_task skills` for current contracts and commands.
Source `scripts/env.bash` from the cell repository (Lyrical, domain64).

The first wall-pinch strategy assumes an upright empty carton on horizontal
support. Its closing axes use image-derived yaw and gravity alignment; observed
tilt above2degrees is rejected. Do not generalize it to inclined or unsupported
objects without a different grasp strategy.

For the first carton recipe, prepare a new immutable contact scene, launch it in
its own `uwa_grasp_lab` world, and run into a fresh output directory. Preserve
other simulations and existing runs. Check whether an own grasp world already
exists before launching another. Scene hashes bind the installed contact plugin;
regenerate the scene after changing that binary.

Use `python3 tools/inspect_manipulation_review.py RUN` from the repository
(or its workspace-relative path) for a compact, hash-verified read-only packet
with current pending status, image paths, candidate data and trajectory bounds.
It never approves a review. A saved packet with pending=false is not a request
to continue.

Use the highest currently allowed and user-approved speed for the task.
Gazebo arm joints are authorized up to 1 rad/s. For drawing playback use
`cell_task prepare --drawing-recipe RECIPE` to select the fast profile.
Any new watcher or test needs the user's explicit permission.
Check the planned trajectories offline. Gazebo plays them through normal
controllers and contact physics. The simulated pad contact triggers the grasp.
Use the recorder only for a requested experiment that needs force or contact
data. `--prepare` creates its separate run directory with a CREATED state.

Historical 500 g translation runs used frozen profiles and guard code. Their
results remain in `setup/tasks/manipulation_qualification_20261116/` and
`docs/carton_dynamic_validation_2026-11-16.md`. Use the current user-selected
speed for new plans.

Keep the runner alive while reviewing from a second tool invocation. At each
`WAITING_REVIEW`, read the current `review.json`, actual images/overlays and
candidate/trajectory evidence; submit its exact SHA with a concrete reason.
The review expires after300s. Within an authorized task the agent performs these
reviews; do not add a human approval step for each checkpoint. `observe` and
`replan` use bounded retries. Never continue merely because the planner returned.

After confirmed two-sided contact at both grippers, command only the common
object frame through `GraspGroup` and its frozen object-to-TCP transforms. The
harness derives both arms with one time law and one12-joint action. Keep other
arms as measured obstacles. Do not replace this with independent arm planning,
retime members separately, or update grasp offsets to conceal slip.

Use `cell_task stop RUN` to cancel the active Gazebo trajectory goals.
Check the run state for the resulting action responses. The simulated gripping
target remains latched until release. Scope process cleanup to the task.

Report only observed results. Software tests, collision-free compiled motion,
visual pose consensus and actual contact-supported lifting are separate evidence.
Rendering truth is an evaluation source, never an estimator prior. The default0.5kg mass is user-reported. Friction, finger damping and rigid
cardboard remain unmeasured simulation assumptions.
Consult HANDOVER for whether complete lifts have actually passed; the existence
of the harness does not establish holding reliability or hardware readiness.
Update HANDOVER and `work/carton-grasp-pipeline.md` with new evidence and limits.

For dynamic experiments read the exploration section of docs/manipulation_pipeline.md.
Use an explicit force-observed profile for a requested load study and the
single shared object law. `simulation_stop_reserve_mode` controls the
offline model only. The earlier guarded force/speed trials are historical.

For the optional longitudinal quarter turn, read `work/carton-roll-90.md` and
`config/carton_roll_90.yaml`. The original end-wall pinch, fixed grasp offsets,
shared object compiler is reused. Nominal geometry needs about146mm
clearance lift, not30mm. The checked left-table placement keeps the opening
facing the fixed OAK camera; direct right-table descent self-collides. Scene04
passes complete dense geometry/timing checks and has a labelled file-only model
animation. This does not establish contact-supported rolling. Initial Home
entry was rejected; the fixture attempt reached four pad contacts but stopped
before pickup on a170ms state gap. The lower-RTF repeat lifts147.7mm but stops near9degrees on2.03mm relative
error. The stronger virtual preload trial stops before pickup on a169ms
state gap. No complete quarter-turn is qualified; see the sealed
`setup/tasks/carton_roll_summary_20261116/result.json` under the workspace. Never use a planned motion as evidence of a completed contact cycle. Phase budgets come from the reviewed trajectory;
the old short lift's generic120s skill metadata does not describe a250s turn.

For a requested real carton test, first read
`docs/carton_hardware_commissioning.md` and
`work/carton-hardware-commissioning.md`. The separate preparation/ROS-gripper
tools default to read-only and have native GET/loopback evidence. The arm task
executor remains simulation-only; do not change its domain or reuse the
independent-progress hardware PTP runner for a loaded rigid group. UR startup
executes no manipulation.17November: shared ROS grippers completed real empty
partial travel raw0→128→0 at SPE16/FOR0 on both right arms; service returned to
MONITOR ONLY. Use the shared API (docs/gripper_ros_api.md), not a duplicate socket
writer/adapter. This does not calibrate force/aperture or qualify loaded stops.
On18November both right URs reached unloaded150mm pregrasp poses using a
fresh ROI texture registration and the current focus107 OAK fit with fixed
user-adopted base bindings. Both final holds, guard quiet and independent quiet
windows passed. See work/carton-pregrasp-20261118.md and the source-bound
setup/tasks/carton_pregrasp_20261118_completed/result.json. All arms remain held,
grippers open/inactive; no finger commands or contact/lift were attempted.
Later18November wrist inspection superseded that current-pose statement:
right front is held in a turned outside inspection pose, while right rear
remains at the old pregrasp. User reports the carton stayed stationary between
wrist captures. The109mm/7.71deg difference between object estimates is not
established physical motion; its cause is unresolved. Old grasp targets require
fresh validation and the wrist stereo pair was rejected. No wrist-centering approval or finger command was
issued. Read work/carton-contact-grasp-20261118.md and
setup/tasks/carton_grasp_20261118_current_check/grasp-status.json before any
continuation. Reobserve a stationary scene and rebuild targets; do not replay
the historical pregrasp result as the current two-arm configuration.
Latest recalculation: setup/tasks/carton_grasp_20261118_scene03/result.json.
Both new150mm high targets and offline replay pass, but real preflight was
rejected before any arm/finger goal after existing manager/hardware verification
freshness limits triggered native STOP. Targets have NOT been reached. Preserve
freshness/stop thresholds; no blind reset/play loop or inferred centering approval.
Keep the current0.1rad/s command limit, without an extra time dilation. Use the
fresh per-base camera transforms rather than substituting nominal world mounts;
check the conservative union of carton representations in the model. Do not
replay old initial joint snapshots. Inactive open grippers do not require an
activation stroke for this approach. CLEAR guard's standstill_confirmed is not
a physical-quiet flag; require fresh stationary_arms for all four before reset.
Keep useful camera settings when requested, retaining the matching intrinsics.
The common object reference core remains transport-free. A loaded coupled
command-delivery/stop/grip backend and real loaded operation are still open.


Hardware continuation after18November user stop: do not resume automatically.
Read docs/carton_supported_grasp.md. The limited supported pipeline is now
prepare_carton_recipe.py → register_carton_from_oak.py → high pregrasp →
carton_gripper_phase.py prepare → open entry → visually checked static close.
Use the versioned hardware_carton_supported.yaml0.1rad/s profile. High/entry
runners use scoped per-arm reset and retain other holds; they do not globally
release/reacquire all four. Do not make a separate regression/simulation campaign
part of normal operation.19November reset/entry passed in the actual run;
closing produced contact but its final standstill/readiness validation failed.
Contact closes to HOLD only,
with frozen common virtual object/TCP offsets; never send independent loaded
arm trajectories. Historical simulation geometry folders may have been removed;
freeze fresh geometry from the canonical asset rather than rewriting old hashes.

The current supported-entry recipe requires one shared object pose derived from
the CURRENT fixed right board and adopted base↔board chains. The older union of
inconsistent global-fit representations was an unloaded pregrasp diagnostic;
do not use it for insertion or exempt another arm from carton collisions.
