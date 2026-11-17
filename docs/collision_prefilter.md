# Conservative arm-AABB prefilter

Implemented2026-11-16 in `uwa_cell_motion`. The shared Python planning validity
check and native RRTConnect worker now skip fine **sphere reserve** queries
when complete arm bounding boxes prove the required clearance. This applies
automatically to RRTConnect, Circular and CDF final/edge checks, and the common
hardware planning model. No new arming action or setting is required.

The17November `per_body_joint_caps_v2` branch also uses this prefilter now.
That new reserve branch initially bypassed the older scalar-threshold path.
For v2, each sphere is expanded by its own full stopping budget before the
arm box is formed. Only separated expanded boxes can skip the existing
`critical_pair` check. Budgets and expanded boxes are recomputed on each query;
only geometry uses the existing dependency-bound cache. The full FCL check
and the runtime guard's exact pair/lease computation are unchanged.

Each axis-aligned box encloses all current collision spheres **including their
radii**. Its Euclidean box-to-box gap is a lower bound on the actual surface
distance. Only a lower bound strictly above the existing pair threshold can
return clear. Box overlap, touching and floating-point equality fall through
to the original fine query. Bounds are rounded outward; a small numerical
guard band makes near-threshold cases use the original decision.

Python planning keeps one current immutable sphere/box snapshot per arm. Cache
keys include every upstream moving joint and mimic source, including gripper
drives. Any dependency change invalidates that arm; incomplete/nonfinite state
is rejected before cache access. The native worker similarly detects moving
arms from model joint ancestry/mimic sources and caches only fixed ones for
that request. A new model/worker starts with an empty cache.

The full MoveIt/FCL collision check still runs, including self, tables, cameras
and tools. Geometry, model hashes, margins, interpolation steps and stopping
budgets are unchanged. The runtime guard's exact distances/nearest points,
circular steering gradients, CDF contact-generation SDF and sampled CDF queries
remain exact to their previous definitions; an AABB gap is never reported as
their measured nearest distance. This is not a whole-trajectory interval proof.

## Evidence

Lyrical build and120 package checks pass, including11 new Python tests and a
native test with3000 random sphere-cloud pairs plus volume/boundary cases.
The30 fixed tasks at9 interpolation states each give270 identical full-cell
decisions against the original implementation, including invalid goals and
crossing/colliding states. Open/closed finger cache invalidation, exact guard
outputs and the166-sphere hardware opening envelope are covered.

`~/UWA_ws/setup/research/aabb-prefilter-v1/report.html` and `result.json` contain
the offline before/after timings. Python timings use five rotated repeats:

| Check | Original ms/state | AABB + cache ms/state | Reduction |
|---|---:|---:|---:|
|150 saved single-UR trajectory states |1.051 |0.734 |30.2% |
|270 states across30 fixed tasks |1.035 |0.771 |25.5% |

The saved trajectory reduces600 fine pair queries to13; the fixed-suite states
reduce1002 to99. These counts include only states reaching the reserve check
after FCL. Complete CDF planning with the same bank and final timing/metrics:
3.112s→2.304s, **identical timed trajectory**. Bank preparation is excluded
because it does not use this new threshold-only filter.

One native RRT trial using the same start, goal, seed and10s budget:
6.913s→1.194s. Both resulting paths pass shared full-cell time-parameterization
validation. Native simplification has a timed budget, so identical output paths
are not claimed; this is a single example, not a general5.8× guarantee.
The native worker's `sphere_prefilter:false` input is used only for this offline
baseline comparison; it retains the original full dense checks.

Earlier geometric estimates are retained in
`setup/logs/uwa-collision-hierarchy-profile.json`; they were not timing claims.
Build/tests: `setup/logs/uwa-prefilter-{build,tests}.log`. No simulation restart,
physical robot command or real-stop qualification was performed.

## Repeat the comparison

### Body-specific hardware reserve comparison,17November

The frozen LF capture approach has166 spheres per arm. On150 identical states,
three rotated repeats give5.316→2.294ms/state; all decisions agree. All600 pair
queries are proved clear by the expanded arm boxes in this particular path.
The complete plan, including time-parameterized validation and exact metrics,
takes20.182→10.074s; the895-point timed trajectory is **identical**. Model
construction takes an additional1.471s. This is one full-plan trial per method,
not a general2× guarantee or a robot stopping qualification.

Evidence: workspace
`setup/calibration/oak_recalibration_20261117/body-prefilter-benchmark-01/result.json`.
Repeat without robot connections or execution:

```bash
source setup/lyrical_env.bash
python3 src/multi_arm_manipulation_UWA/uwa_cell_motion/test/benchmark_body_prefilter.py \
  --plan setup/calibration/oak_recalibration_20261117/hardware-views-01/01e-left_front/plan.json \
  --output setup/calibration/oak_recalibration_20261117/body-prefilter-new-run
```

### Original scalar-threshold comparison

From `~/UWA_ws` after building the package:

```bash
source setup/lyrical_env.bash
python3 src/multi_arm_manipulation_UWA/uwa_cell_motion/test/benchmark_prefilter.py \
  --trajectory setup/research/cdf-ur-comparison-v2/blocked_direct_04-0-cdf.json \
  --output setup/research/aabb-prefilter-new-run --native
```

Use a fresh output directory. The script checks old/new decisions on identical
states, compares the complete CDF trajectory and validates native plans. It
never connects to robots. The trajectory/model/limits and neighboring
`contacts-0.npz` must match. Another cell-model instance has its own cache;
no persisted geometry cache can silently outlive a model change.
