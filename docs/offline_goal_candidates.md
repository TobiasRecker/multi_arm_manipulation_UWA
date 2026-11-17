# Offline goal candidates

## View the results

Open the [interactive endpoint viewer](../../../setup/research/offline-goal-candidates-20261117/viewer.html)
in a browser (HTML source view in an editor does not run the viewer).
Choose **Checked combinations** for the 16 jointly validated model endpoints,
or **Individual IK candidates** to inspect eight alternatives per arm. The
latter shows other arms at their start and does not claim combined validity.
Drag to rotate, scroll to zoom. Positions switch directly; there is no checked
connecting path. Full-turn joint alternatives can look identical.

For this Markdown guide in VS Code: **Ctrl+Shift+V** opens the rendered preview;
**Ctrl+K**, then **V** opens it beside the source. Tables, links, images and
code blocks are rendered there. Interactive HTML should open externally.

First implementation stage, 2026-11-17. `cell_goal_candidates` enumerates
multiple endpoint configurations before any path planner commits to one.
It loads the existing cell model offline and sends no ROS actions or commands.
The current scope is explicit task target poses/joint alternatives with fixed
model base poses. Automatic grasp synthesis and moving-base trajectories remain
subsequent stages.

## Input

A JSON object contains `schema_version: 1`, the complete `start` mapping used by
`cell_motion` (all four arms and gripper driving joints), and `goals` for one
or more known arms. Each goal accepts one of:

- `{"positions": [q1, q2, q3, q4, q5, q6]}` in radians;
- `{"frame_id": "world", "target_link": "right_rear_tool0", "pose":
  {"position": [x,y,z], "orientation_xyzw": [x,y,z,w]}}`;
- `{"alternatives": [goal1, goal2, ...]}` with either form above.

Positions are metres, quaternion order is XYZW. Use an explicit, existing link
belonging to the selected arm. `tool0` is the flange frame, not an assumed
calibrated grasp TCP. Supply the appropriate model link or externally converted
flange pose. Gripper states remain frozen in this first arm-only stage.

## Build and run

From `~/UWA_ws`:

```bash
source setup/lyrical_env.bash
colcon --log-base log_lyrical build --base-paths src \
  --build-base build_lyrical --install-base install_lyrical \
  --packages-select uwa_cell_motion --symlink-install
source install_lyrical/setup.bash
ros2 run uwa_cell_motion cell_goal_candidates \
  setup/research/offline-goal-candidates-20261117/request.json \
  --layout setup/research/offline-goal-candidates-20261117/layout-original.yaml \
  --output /tmp/uwa-goal-candidates-new.json --seeds 24 --budget 60
```

Choose a fresh output path. `--base-paths src` avoids discovering immutable
experiment snapshots under `setup/tasks` as duplicate packages. The example
requests the four nominal start flange poses, deliberately testing multiple IK
representations of the same task poses, not a hardware target or travelled path.
`request-offsets.json` additionally offers two changed flange orientations per
arm. The examples bind the original 0.90 m table-base spacing: a concurrent
update changed the shared default to 0.991 m during verification. Use the saved
layout for these examples; no shared layout was reverted. A complete generated
URDF and mesh hashes accompany the historical results. Joint vectors differing
by allowed full revolutions can remain distinct; eight candidates do not imply
eight distinct geometric IK branches.

## Search and interpretation

Bounded multistart least-squares IK uses the existing URDF chain, joint limits
and deterministic random seeds. Default 16 starts per pose, up to 8 candidates
per arm, 256 combined endpoint checks and 16 returned combinations. Options:
`--seeds`, `--seed`, `--budget`, `--max-per-arm`, `--max-checks`,
`--max-combinations`, `--layout`, `--config`.

Position and orientation residuals are checked separately at 0.1 mm and
0.1 mrad in model coordinates. These are solver tolerances, not physical
calibration accuracy. Duplicate configurations within 0.1 mrad Euclidean joint
distance merge their alternative indices. Bounded joint coordinates are not
wrapped modulo 2*pi across joint/cable limits.

Per-arm candidates are explicitly `KINEMATIC_ONLY`. Other selected arms may
move away, so filtering each arm against their start poses would discard valid
combined endpoints. Cost-ordered combinations are checked with full-cell FCL,
existing planning neighbor reserves, and static sphere clearance of at least
`model_margin_m` on all six arm pairs. Inactive arms stay at their supplied
start. Only combined results are marked `MODEL_ENDPOINT_VALID`.

The ranking is the sum of joint-space Euclidean displacements from start;
it is a simple ranking heuristic, not predicted travel time or optimality.
A bounded heap traverses retained candidate combinations without allocating the
entire Cartesian product. Original goal alternatives, start, model signature,
mesh hashes, configuration, search settings and diagnostics are included.

`CANDIDATES_FOUND` means at least one combined endpoint passed. Every result
has `executable: false`. No edge, path, timing or controller interpolation is
validated. `NO_VALID_COMBINATION_FOUND` does not prove infeasibility. Deadline,
retained candidates, cap truncation and remaining combinations are reported;
IK is never claimed complete. The deadline is checked during solver evaluations
and between model checks; a single geometry call is not preempted. Model loading
precedes the search budget. CLI exit 2 denotes no valid combination (or input
usage error); malformed input may also raise a descriptive exception.

## Evidence

Targeted tests cover four-arm endpoints, all six pairs, alternative retention,
deduplication, multiple IK solutions with FK reconstruction, invalid inputs,
unreachable targets, deadline/cap reporting and rejection of colliding combined
states without deleting their individual kinematic candidates. Current run
results are recorded in HANDOVER and `work/offline-goal-candidates.md`.

Installed CLI evidence: both examples retained eight candidates per arm and
16 valid combined endpoints within their output cap. All 64 retained candidate
poses and 32 combined endpoints were independently recomputed with the matching
model (`setup/research/offline-goal-candidates-20261117/verification.json`).
This validates endpoints in two small examples, not representative planning
success or physical accuracy. The geometric start poses are nominal model data.

The plan PDF is [UWA offline planning](../output/pdf/uwa_offline_multiarm_plan_2026-11-17.pdf).
The [research survey](mobile_multiarm_planning_survey_2026-11-16.md) explains
later path coordination and learned comparisons.
