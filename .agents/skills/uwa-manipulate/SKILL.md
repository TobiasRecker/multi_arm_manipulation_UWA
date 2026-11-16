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

Use the documented0.6 real-time-factor/1ms physics profile and workstation CPU
configuration before recipes. For independent validation, start the recorder
with `tools/trace_manipulation.py RUN --prepare` before starting the runner;
verify its trace file exists and allow discovery to settle before reset/arming.
Avoid introducing new ROS participants while armed. A constructor-only RunStore
does not persist state; `--prepare` explicitly creates the CREATED state.

The nominal Home recipe defaults to0.5mm/s object speed. Read the case-specific
evidence in `setup/tasks/manipulation_qualification_20261114/result.json` under
the workspace root: earlier1mm/s passes use different start/mass profiles.
Nominal Home at1mm/s and the0.4kg/friction0.8 case failed the passive-finger
speed limit. Do not infer an untested operating region from successful cases.
The nominal0.5mm/s repetition also failed this limit before pickup (run74),
despite the completed individual run71. Nominal grasp repeatability remains
unresolved; keep the default labelled experimental and report aborted attempts.

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
Rendering truth is an evaluation source, never an estimator prior. Mass,
friction, finger damping and rigid cardboard are unmeasured simulation assumptions.
Consult HANDOVER for whether complete lifts have actually passed; the existence
of the harness does not establish holding reliability or hardware readiness.
Update HANDOVER and `work/carton-grasp-pipeline.md` with new evidence and limits.
