# Object-led manipulation skills (simulation)

The first recipe is `avocado_carton`, `right_front` + `right_rear`, empty rigid
carton, 30 mm lift, two-second dwell, set down and release. The task transport
cannot address hardware. It requires domain64, `uwa_cell_sim`, LOCALHOST and an
isolated `/uwa_grasp_*` namespace. No real power, brake or program commands exist.

## Agent workflow

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

- All transforms are right-handed4×4 matrices, metres, +Zup. Twists are
  `[vx,vy,vz,wx,wy,wz]` at the object origin in the common world frame.
- `scene.json` binds geometry/configuration; approach plans bind the complete
  measured start, object geometry, model and selected grasp. JSON artifacts
  carry a SHA256 over canonical contents.
- Observation is `uwa_cell_tracking` static image registration with the matching
  simulated CameraInfo and stationary-joint audit. Camera processing is a child
  process. Simulator truth does not initialize or choose its solution.
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

## Contact model and limits

The original visual-only carton and ordinary cell launch remain available.
The opt-in scene extrudes the asset's outer skin triangles into convex thin
prisms, preserving the open interior and observed upper cutouts. It computes
mass properties from those volumes and uses real gravity/contact. No attachment
joint or pose teleportation is used for grasping or lifting.

The contact gripper backend applies bounded PD torques to physical finger
joints. Its coupling is a compliant approximation, not a validated reproduction
of the adaptive Robotiq transmission. Finger positions are measured, not copied
from mimic targets. Applied motor torque is labelled as such, not contact force.

Defaults in `config/carton.yaml`: mass0.3kg, friction0.6 and thickness2.5mm are
unmeasured simulation assumptions. Rigid cardboard cannot establish crushing
strength or real holding reliability. Native real-camera calibration and the
preliminary physical world anchors are not improved by this simulation.

Five complete physical-contact lifts, mass/friction variations and fault tests
are the intended acceptance. Only actually completed tests in HANDOVER count
as evidence; merely having these commands is not a successful grasp result.

RViz must use the private TF topics `/uwa_grasp_validation/tf` and `tf_static`,
the private robot description, and `/uwa_grasp_validation/tasks/markers`.
The marker labels simulator truth explicitly and displays group/stop state in text.
