# Four-arm offline motion planning and Gazebo playback

The simulation runs in ROS domain 64 and partition `uwa_cell_sim`.
The [hardware backend](four_arm_hardware_motion.md) uses a separate domain
and its own runtime protection. MoveIt/FCL and the modeled clearance reserve
check planned configurations and their interpolation offline.

Build the packages in the Lyrical workspace, then start Gazebo normally.
Use `image_sensors:=false` when the demo needs no rendered camera feeds.
The trajectory controllers receive timed goals directly. For a multi-arm
plan each controller receives its columns with the same simulation start
time. Ctrl+C cancels the goals of the current playback process.

## Request, plan and preview

```bash
ros2 run uwa_cell_motion cell_motion snapshot --output /tmp/uwa-start.json
```

The request has `schema_version:1`, a complete `start` joint-position mapping
(radians, including the four gripper drive joints) and `goals` keyed by arm ID.
Use six joint angles per selected arm. Unselected arms remain scene obstacles.
This interface positions free arms. Rigid multiarm carrying uses the cooperative
object-pose controller and its fixed object-to-TCP constraints.
Include every arm intended to move in `goals`. The plan treats all other
arms and grippers as fixed at their start snapshot.

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
mesh CCD. The executor rechecks the timed plan offline before sending it
to Gazebo and saves the exact applied trajectory. Controller replies record
the outcome of playback.

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
paths. It uses the running cell’s regular trajectory controllers. Individual results and `summary.json` are saved
incrementally; an interrupted comparison resumes from existing bound results.
Offline successes and execution successes remain separate metrics.
`replay-comparison` groups identical complete start/timed-trajectory pairs and
links the physical execution record to each repeat. A newly failed execution
aborts the batch and saves the controller outcome.
`scenarios` can generate a new suite, but the checked-in suite freezes this
comparison. Neighbor crossings have verified conservative sphere intersection;
that does not imply physical mesh contact in every crossing.

## Historical evidence from the guarded prototype (2026-11-13)

The final offline set is `setup/logs/uwa-motion-comparison-v4/`:300 trials,
10s per planner query,30 fixed tasks and five seeds. RRTConnect succeeded in
102/125 valid-goal attempts and the circular baseline in115/125. Both rejected
all25 intentionally invalid goals. Neighbor-crossing success was3/25 versus
15/25. This is evidence for this suite, not a general planner ranking.
For free PTP tasks where completion matters more than the particular path,
the study recommendation is to prefer the circular baseline provisionally and
retain RRTConnect as the reference. This follows the higher measured success
rate; individual RRT paths can be shorter, and hardware remains a separate stage.
The250 unchanged trials retain explicit provenance to the previous comparison;
the50 corrected crossing trials use the same frozen model/configuration.

All55 distinct complete-start/timed trajectories representing217 successful
plans were attempted in Gazebo:53 completed, two RRT crossing executions stopped
(gripper velocity0.05835rad/s above the0.05 operating cap; a152ms state-processing
gap). Linked trials give100/102 RRT execution successes and115/115 circular
successes. Exact repeats share physical evidence. All earlier failed preparations,
development versions and interruptions remain in the report's attempt history;
the118 retained attempts/18 failures span different development conditions.
The data audit confirms one collision model/mesh set, planned speed/acceleration
bounds and a maximum recorded successful endpoint error of0.461mrad.

The final66 motion tests passed(70 including four CTest wrappers), alongside
36 Gazebo model/overview checks. Final live evidence is
`setup/logs/uwa-motion-live-guard-check-executor-acceptance.json`; the report is
`setup/logs/uwa-motion-comparison-v4/report.html`. The comparison ended with all
four simulated arms resource-held and measured stable, without automatic resume.
Source/runtime revisions are explicit in the manifest. Unused middleware warning
callbacks were removed after profiling; actual clock/freshness/heartbeat checks
and transport QoS remain. This reduces bookkeeping without guaranteeing deadlines.

The earlier fault-injection tool and guard launch were retired on 19 November.
The results above describe the historical implementation.

Full-cell validation uses the shared rendered URDF, allowed-collision rules and
floor. Arbitrary Gazebo-spawned obstacles, visual-only scan points, cables and
unmodeled attachments are not automatically imported. Geometry changes require
a fresh model, plan and suite.

Sources: [CDF](https://arxiv.org/html/2406.01137v1),
[Informed Circular Fields](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2024.1447351/full),
[OMPL integration](https://moveit.picknik.ai/humble/doc/examples/ompl_interface/ompl_interface_tutorial.html).
