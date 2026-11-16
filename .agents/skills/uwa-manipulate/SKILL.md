---
name: uwa-manipulate
description: Compose and review object-led manipulation tasks in the UWA digital robot cell, including two-arm carton grasps and rigid cooperative handling. Uses the simulation task harness; physical robot execution is not implemented.
---

Read the repository AGENTS.md and current manipulation section in HANDOVER.md.
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

Use the documented0.6 real-time-factor/1ms commissioning profile (or an
explicit0.1–1ms exploration refinement with separate evidence) and workstation CPU
configuration before recipes. For independent validation, start the recorder
with `tools/trace_manipulation.py RUN --prepare` before starting the runner;
verify its trace file exists and allow discovery to settle before reset/arming.
Avoid introducing new ROS participants while armed. A constructor-only RunStore
does not persist state; `--prepare` explicitly creates the CREATED state.

For a new500g translation task use the tested fast profile from
`setup/tasks/manipulation_qualification_20261116/result.json` under the workspace
root: source the normal cell environment, then the recorded frozen
`environment.bash`, and pass its explicit `qualified-profile.yaml`. The compact
report `docs/carton_dynamic_validation_2026-11-16.md` contains the exact command.
Two full10mm/s Home cycles and three loaded stops pass with the same0.2rad/s
finger envelope and fully retained stopping reserve. This is a finite observed
profile, not a physical speed maximum or a rotation/hardware qualification.
The package default remains the old slow commissioning profile; do not select it
merely because no config was supplied. Old14November evidence used other masses
and includes repeat failures; preserve it without applying it to500g.

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

On failure inspect state, primary guard causes and confirmed holds. Arm stopping
retains grip; no automatic opening, return or resume. A fresh run is not a way to
reset a loaded grasp group. Use `cell_task stop RUN` and wait for confirmed
standstill when abandoning an active run. Scope process cleanup to this task.

Report only observed results. Software tests, collision-free compiled motion,
visual pose consensus and actual contact-supported lifting are separate evidence.
Rendering truth is an evaluation source, never an estimator prior. The default0.5kg mass is user-reported. Friction, finger damping and rigid
cardboard remain unmeasured simulation assumptions.
Consult HANDOVER for whether complete lifts have actually passed; the existence
of the harness does not establish holding reliability or hardware readiness.
Update HANDOVER and `work/carton-grasp-pipeline.md` with new evidence and limits.

For dynamic experiments read the exploration section of docs/manipulation_pipeline.md.
Use an explicit force-observed exploration profile, preserve per-DOF stopping
reserves and the single shared object law. Commissioning reports do not qualify
new speed profiles. Planned jerk limits do not qualify real actuator jerk or
loaded stops.50N is a user-reported reference per jaw/wall patch, not a measured
material failure limit. Direct force reference tests passed; no floating base
is presently required. The finite experiment driver completed two negative5/10mm/s cases with force
evaluation and scoped cleanup. Both carried500g to29.4mm and stopped at a
configured passive-finger speed bound during descent. After increasing only
virtual motor preload, a5mm/s fixture cycle and two complete10mm/s Home cycles
with500g passed (gap-free forces,29.924mm lift,<=0.274mm relative position error,
<=5.556N per-jaw peak upper bound). The final0.2rad/s-finger profile additionally passes two full Home repeats
and all three loaded faults; the sealed16November index binds their common
profile/implementation. Its largest per-jaw peak upper bound is5.504N. No physical speed maximum or hardware setting is qualified.
Preserve the older negative evidence and narrower source-binding scope.

For the optional longitudinal quarter turn, read `work/carton-roll-90.md` and
`config/carton_roll_90.yaml`. The original end-wall pinch, fixed grasp offsets,
shared object compiler and guard are reused. Nominal geometry needs about146mm
clearance lift, not30mm. The checked left-table placement keeps the opening
facing the fixed OAK camera; direct right-table descent self-collides. Scene04
passes complete dense geometry/timing checks and has a labelled file-only model
animation. This does not establish contact-supported rolling. Initial Home
entry was rejected; the fixture attempt reached four pad contacts but stopped
before pickup on a170ms state gap. A single lower-RTF repeat is pending. Never
weaken freshness limits to make the experiment pass or present planned motion
as a completed contact cycle. Phase budgets come from the reviewed trajectory;
the old short lift's generic120s skill metadata does not describe a250s turn.
