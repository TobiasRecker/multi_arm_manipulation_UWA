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
bash src/multi_arm_manipulation_UWA/scripts/motion.sh start
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
`motion.sh status` and `motion.sh logs` inspect the managed user service
`uwa-cell-motion`. `motion.sh stop` first requests and confirms all four holds,
then ends only that service. It leaves Gazebo and all hardware services alone.
For a foreground session, use `ros2 launch uwa_cell_motion guard.launch.py`
instead; do not start a second guard beside the managed service.

The geometric process publishes `/uwa_cell/collision_guard/decision`,
`/uwa_cell/collision_guard/diagnostics` and MarkerArray
`/uwa_cell/collision_guard/markers`. The standard cell RViz configuration includes
this display (fixed frame `world`). An already-open RViz can add this MarkerArray
with reliable/volatile QoS. Surface-nearest points, pair distances, data ages,
large text states and a permanent provisional-anchor notice accompany spheres.
The independent supervisor publishes
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
Standstill confirmation uses the measured independent arm/tool drives used by
the guard and FK model. Passive mimic joints follow that coupling model;
their Gazebo solver velocity noise does not count as commanded drive motion.
Missing/nonfinite drive measurements prevent confirmation.

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
Reset can release eligible arms individually: with LF state missing, RR may
be reset while LF/RF/LR remain held. Source-clock reversal also latches a stop.
The geometric check uses10Hz monotone wall time, independently of physics
speed. State/heartbeat age and the supervisor watchdog also use wall time.
Pausing Gazebo continues the checks and latches `STATE STALE` when source
timestamps stop advancing. Source timestamps and RViz markers use ROS time.
The supervisor also expires each pair's geometric decision before its last
distance reserve is consumed. Excess clearance buys extra waiting time, capped
by the400ms heartbeat limit; a close pair can expire sooner. Same-host
monotonic evaluation timestamps include computation and transport age, and
the20ms supervisor period is deducted from the lease. The stop budget assumes
the default real-time factor at most1; accelerated physics is unsupported.

## Request, plan and preview

```bash
ros2 run uwa_cell_motion cell_motion snapshot --output /tmp/uwa-start.json
```

The request has `schema_version:1`, a complete `start` joint-position mapping
(radians, including the four gripper drive joints) and `goals` keyed by arm ID.
Use six joint angles per selected arm. Unselected arms remain scene obstacles.
They must stay stationary. Include every arm intended to move in `goals`;
an unselected arm moving during execution invalidates the job and stops the
job's owned arms. This does not globally prohibit independent ROS motion.
Tool drives also stay at their complete-start values during these arm-only
trajectories; external gripper movement invalidates the remaining PTP path.
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

For a single arm among measured stationary obstacles, the executor submits the
complete revalidated timed trajectory. It monitors the measured geometric
corridor (1mrad), source-clock progress, stationary obstacles and full-cell FCL
checks every50ms simulation time. A harmless temporal lag on that same path is
recorded separately. The exact applied trajectory is saved with the execution.

Multiarm execution uses short independently safe phases and measured endpoint
barriers. It can wait for unequal progress. After a pair stop it rechecks the
remaining phases against the current arms and a braking-displacement envelope.
The executor recomputes quintic timing within the same limits for these phases;
actual execution time includes barriers and can exceed offline planned timing.
Interrupted execution requests persistent per-arm latches and resource holds
before closing ROS; its result records whether those were confirmed.

## Reproducible comparison

```bash
ros2 run uwa_cell_motion cell_motion coverage --output /tmp/uwa-coverage.json
ros2 run uwa_cell_motion cell_motion benchmark \
  src/multi_arm_manipulation_UWA/uwa_cell_motion/config/benchmark_suite_20261113.json \
  --output setup/logs/uwa-motion-comparison
ros2 run uwa_cell_motion cell_motion replay-comparison setup/logs/uwa-motion-comparison
ros2 run uwa_cell_motion cell_motion report setup/logs/uwa-motion-comparison \
  --output setup/logs/uwa-motion-comparison/report.html
```

The suite has30 verified tasks, five each: free, blocked direct path,
neighbor crossing, four arms, near-tool passage and unreachable goal.
Generation fails rather than silently mislabeling missing categories. Five
fixed seeds and10s planner budget give300 attempts. Normalization is shared;
final validation time is recorded separately from planning time. Every failure,
including invalid goals and timeouts, stays in the denominator. The raw per-run
artifacts retain duration, path length and minimum sphere clearance.
Native and Python joint-limit checks share a numerical tolerance of1e-8rad,
including measured gripper positions near zero. Larger violations stay invalid.

`--limit` and `--seeds` select a smoke comparison. `--execute` also executes each
successful result in Gazebo and repositions to its start through checked RRT
paths, never by teleporting the cell. It requires an armed, reset guard and an
otherwise idle simulation. Individual results and `summary.json` are saved
incrementally; an interrupted comparison resumes from existing bound results.
Offline successes and execution successes remain separate metrics.
`replay-comparison` groups identical complete start/timed-trajectory pairs and
links the physical execution record to each repeat. A newly failed execution
aborts the batch with the latch retained. Review the saved cause before an
explicit reset/new invocation; the batch never resets a stop automatically.
`scenarios` can generate a new suite, but the checked-in suite freezes this
comparison. Neighbor crossings have verified conservative sphere intersection;
that does not imply physical mesh contact in every crossing.

## Evidence and current limits (2026-11-13)

The final offline set is `setup/logs/uwa-motion-comparison-v4/`:300 trials,
10s per planner query,30 fixed tasks and five seeds. RRTConnect succeeded in
102/125 valid-goal attempts and the circular baseline in115/125. Both rejected
all25 intentionally invalid goals. Neighbor-crossing success was3/25 versus
15/25. This is evidence for this suite, not a general planner ranking.
The250 unchanged trials retain explicit provenance to the previous comparison;
the50 corrected crossing trials use the same frozen model/configuration.

The live guard check injects proximity/stale-state faults in a separate test
fixture while moving Gazebo joints. It exposes no fault-injection service in
production. It checks pair scope, continued independent motion, multiple
faults, topic commands, controller reactivation, state loss and missing guard.
It also pauses physics while all arms are held, verifies continued wall-time
checks and `STATE STALE`, and restores physics before moving. Successful
observed latencies are measurements, not guaranteed worst-case bounds.
Run it only with the normal motion service stopped:

```bash
bash src/multi_arm_manipulation_UWA/scripts/motion.sh stop
python3 src/multi_arm_manipulation_UWA/uwa_cell_motion/test/live_guard_check.py \
  --own-supervisor --output /tmp/uwa-guard-check.json
bash src/multi_arm_manipulation_UWA/scripts/motion.sh start
```

Full-cell validation uses the shared rendered URDF, allowed-collision rules and
floor. Arbitrary Gazebo-spawned obstacles, visual-only scan points, cables and
unmodeled attachments are not automatically imported. Geometry changes require
a fresh model, plan and suite; the controller manager must load matching hold
parameters. Simulation stop measurements establish no real braking reserve.

Sources: [CDF](https://arxiv.org/html/2406.01137v1),
[Informed Circular Fields](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2024.1447351/full),
[OMPL integration](https://moveit.picknik.ai/humble/doc/examples/ompl_interface/ompl_interface_tutorial.html).
