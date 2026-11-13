# Four-arm collision guard and PTP comparison

This first version commands **Gazebo simulation only**, ROS domain64,
partition `uwa_cell_sim`. It does not start or stop real UR programs.
The model's physical world/table anchors remain provisional.

## Build and arm

From the workspace:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
colcon --log-base log_lyrical build --build-base build_lyrical \
  --install-base install_lyrical --packages-select uwa_cell_motion
source install_lyrical/setup.bash
ros2 launch uwa_cell_motion guard.launch.py
```

The cell must already be running. The controller manager must have inherited
the updated installation environment so pluginlib can discover the new plugin.
Starting the guard explicitly puts the four simulated arms into resource-held
stop. After fresh state, clear distances and confirmed standstill:

```bash
ros2 run uwa_cell_motion cell_motion reset
```

Reset releases the hold controllers; trajectory controllers remain inactive.
Execution or the operator must explicitly activate them. No automatic resume.

The geometric process publishes `/uwa_cell/collision_guard/decision`,
`/uwa_cell/collision_guard/diagnostics` and MarkerArray
`/uwa_cell/collision_guard/markers`. Add the markers in RViz with fixed frame
`world`. The independent supervisor publishes
`/uwa_cell/collision_supervisor/status`. Text states accompany colors.
An explicit arm stop is available at
`/uwa_cell/collision_supervisor/<robot_id>/stop` (`std_srvs/Trigger`).

## Stop behavior and assumptions

The four undirected pairs are LF/RF, LF/LR, RF/RR, LR/RR. A distance violation
latches its two endpoints; simultaneous faults combine their endpoints. A lost
arm state affects its two neighbor pairs. A lost geometric process latches all
four arms because no pair then has current supervision.

Each arm's `CollisionHold` controller takes its position resources, including
the gripper drive, decelerates measured joint velocities and holds the stopped
positions. The supervisor deactivates conflicting controllers and monitors
reactivation attempts. A trajectory topic cannot write through an active hold
controller. An operator deliberately replacing the hold controller in an
explicit controller-manager switch can defeat this software interlock; the
supervisor will request it again. It is not a hardware safety function.

The sphere model encloses every local collision-body AABB by circumspheres of
complete slices. All modeled collision volume is covered, including finger
motion through mimic FK. This is deliberately conservative and depends on the
accuracy of the underlying collision meshes. It does not model loose cables,
people or the currently visual-only OAK tripod.

For each arm the guard bounds all-body Cartesian speed using joint-axis
lever-arm bounds. A pair's stop threshold is:

```
model margin + sum over both arms of
  [all-body speed bound × (check interval + state age + stop latency)
   + joint-space braking-displacement bound]
```

`config/motion.yaml` contains simulation design assumptions:10Hz, joint motion
limit0.05rad/s, acceleration0.10rad/s², hold deceleration0.5rad/s²,
state timeout0.15s, switch latency budget0.10s and geometric margin20mm.
Planner validation reserves the full state-timeout budget. The guard uses
actual state age and at least the configured velocity bound. Overspeed causes
a latched stop. Arbitrarily faster external commands are outside this operating
envelope; no measured/certified protection at arbitrary commanded speeds is
claimed. Measured stop latency must fit the configured budget.

Replayed messages with unchanged source timestamps do not refresh state
liveness. Reset requires fresh clear geometry,10mm extra hysteresis and a
stationary history. A guard restart or heartbeat recovery cannot clear a latch.

## Request, plan and preview

```bash
ros2 run uwa_cell_motion cell_motion snapshot --output /tmp/uwa-start.json
```

The request has `schema_version:1`, a complete `start` joint-position mapping
(radians, including the four gripper drive joints) and `goals` keyed by arm ID.
Use six joint angles per selected arm. Unselected arms remain scene obstacles.
Example goal form:

```json
{"goals":{"left_front":{"positions":[0,-1.57,0,-1.57,0,0]}}}
```

These example angles are a format demonstration, not a checked target.
Cartesian goals use `frame_id:"world"`, an explicit arm `target_link` and
`pose:{position:[x,y,z],orientation_xyzw:[x,y,z,w]}`. Targets are normalized to
joint goals before comparing methods, using deterministic IK and the same
chosen result for both methods.

```bash
ros2 run uwa_cell_motion cell_motion plan request.json --method rrtconnect \
  --seed 0 --output /tmp/rrt-plan.json
ros2 run uwa_cell_motion cell_motion plan request.json --method circular \
  --seed 0 --output /tmp/circular-plan.json
ros2 run uwa_cell_motion cell_motion preview /tmp/rrt-plan.json \
  --output /tmp/rrt-preview.html
ros2 run uwa_cell_motion cell_motion execute /tmp/rrt-plan.json \
  --output /tmp/rrt-execution.json
```

Preview is a standalone, high-contrast HTML joint-path plot; it sends no motion.
Results bind the collision model, meshes, complete start and configuration.
Execution rejects a changed model or a different measured start.

RRTConnect uses native OMPL with full-cell MoveIt/FCL validity and the same
sphere-clearance reserve used in final validation. The circular baseline uses
whole-body sphere control points, analytic Jacobians, six rotation hypotheses,
neighbor-relative steering and oriented environment-body boxes for steering.
It is **CF-inspired**, not a reproduction of Informed Circular Fields. It
never invokes RRT. Failure to leave a trap remains a reported failure.

Both paths receive conservative stop-at-waypoint quintic timing, and identical
full-scene checks after timing. This includes self/table/tool/camera collisions,
and all other arms, including diagonals in the full FCL scene. Collision
sampling is at most5mrad per joint; this is discrete checking, not continuous
mesh CCD. The execution phases add conservative interarm displacement bounds.

The executor uses short independently safe phases and measured endpoint
barriers. It can wait for unequal progress. After a pair stop it rechecks
remaining phases against the current arms and a braking-displacement envelope.
Actual execution time includes these barriers and can exceed offline timing.

## Reproducible comparison

```bash
ros2 run uwa_cell_motion cell_motion coverage --output /tmp/uwa-coverage.json
ros2 run uwa_cell_motion cell_motion scenarios --output /tmp/uwa-suite.json
ros2 run uwa_cell_motion cell_motion benchmark /tmp/uwa-suite.json \
  --output setup/logs/uwa-motion-comparison
```

The suite has30 verified tasks, five each: free, blocked direct path,
neighbor crossing, four arms, near-tool passage and unreachable goal.
Generation fails rather than silently mislabeling missing categories. Five
fixed seeds and10s planner budget give300 attempts. Normalization is shared;
final validation time is recorded separately from planning time. Every failure,
including invalid goals and timeouts, stays in the denominator. The raw per-run
artifacts retain duration, path length and minimum sphere clearance.

`--limit` and `--seeds` select a smoke comparison. `--execute` also executes each
successful result in Gazebo and repositions to its start through checked RRT
paths, never by teleporting the cell. It requires an armed, reset guard and an
otherwise idle simulation. Individual results and `summary.json` are saved
incrementally; an interrupted comparison resumes from existing bound results.
Offline successes and execution successes remain separate metrics.

Sources: [CDF](https://arxiv.org/html/2406.01137v1),
[Informed Circular Fields](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2024.1447351/full),
[OMPL integration](https://moveit.picknik.ai/humble/doc/examples/ompl_interface/ompl_interface_tutorial.html).
