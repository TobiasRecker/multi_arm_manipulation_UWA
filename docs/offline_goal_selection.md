# Offline joint goal selection — step 2

Open the [interactive result](../../../setup/research/offline-goal-selection-20261117/task-alternatives/viewer.html)
in a browser. The comparison table selects three representative endpoints;
the plot shows the tradeoff across all valid evaluated combinations. Orbit,
zoom, six arm-pair gaps and individual IK candidates remain available.

This example uses four synthetic, equally acceptable flange poses per arm,
with multistart IK retaining eight candidates per arm. It is a demonstration,
not a real manipulation task. The frozen model uses the current 0.991 m rear
base spacing. Bases and grippers stay fixed. **No connecting paths, timing or
robot commands are produced.**

## What step 2 adds

Step 1 stops after a bounded number of valid combined endpoints. Step 2 searches
the retained per-arm candidate product independently of that output cap. It
checks model/mesh/configuration identity and rechecks each saved candidate's
joint bounds and task-pose provenance before using it. Changed start distances
or validation labels in a file are not trusted as computed evidence.

A six-pair compatibility cache rejects arm-pair conflicts. It uses the existing
four-neighbour planning reserves plus at least the static model margin for
every pair, including diagonals. Every surviving full endpoint is additionally
checked against the existing complete FCL scene and planning margins. This
includes tables, tools and self-collision represented by that scene; the
six-pair cache alone is insufficient. Unselected arms stay at the input start.

The three objectives are:

| Criterion | Definition | Preference |
|---|---|---|
| Joint displacement | Sum over selected arms of Euclidean six-joint displacement from start, in radians | Smaller |
| Arm clearance | Minimum surface gap of conservative sphere models across all six arm pairs, in metres | Larger |
| Joint-limit reserve | Smallest distance to a bound divided by that joint's entire allowed range, over selected arm joints | Larger |

Joint-limit reserve is at most 50%; it is neither a singularity measure nor
manipulability. Joint displacement is neither validated path length nor travel
time. Joint coordinates are not wrapped modulo 2*pi. Full-turn alternatives
remain distinct even when their endpoint geometry looks the same.

A candidate is Pareto-dominated when another is no worse in all three criteria
and better in at least one. Metrics are rounded to six decimals for this
comparison and policy tie-breaking, avoiding meaningless solver-level
differences. Raw metrics remain stored. Thus Pareto membership has a stated
numerical resolution, not an exact real-number optimality claim.

Default shortlist: the Pareto endpoint with least joint displacement, the one
with greatest arm clearance, and the one with greatest joint-limit reserve.
Duplicate winners are merged; remaining slots use Pareto alternatives ordered
by displacement. Deterministic ties favour clearance, then joint reserve,
then the endpoint ID. No arbitrary weighted sum is used. Other retained
candidates and all valid evaluated combinations remain in the artifact for
later goal/path fallback. Up to three goals are shortlisted by default; if
the frontier has fewer, fewer are returned.

## Run and reproduce

Build the motion package as in [step 1](offline_goal_candidates.md#build-and-run).
From `~/UWA_ws`, using fresh output paths:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 run uwa_cell_motion cell_goal_selection \
  setup/research/offline-goal-selection-20261117/task-alternatives/candidates.json \
  --layout setup/research/offline-goal-selection-20261117/task-alternatives/layout.yaml \
  --max-checks 4096 --budget 60 --shortlist-size 3 \
  --output /tmp/uwa-goal-selection.json
python3 src/multi_arm_manipulation_UWA/tools/preview_goal_candidates.py \
  /tmp/uwa-goal-selection.json \
  --urdf setup/research/offline-goal-selection-20261117/task-alternatives/model.urdf \
  --description "Synthetic task alternatives; no measured task or real motion target." \
  --output /tmp/uwa-goal-selection.html
xdg-open /tmp/uwa-goal-selection.html
```

`tools/build_goal_selection_demo.py --output-dir /tmp/uwa-selection-demo-new`
rebuilds synthetic Cartesian target alternatives and IK candidates using a
snapshot of the current default layout. A changed model intentionally produces
a new example; the saved results above retain their original model binding.
Run the selector on the new candidates with that new directory's layout.

CLI options: `--layout`, `--config`, `--max-checks` (default4096), `--budget`
(default60seconds), `--shortlist-size` (default3). Budget checks occur between
complete endpoint evaluations; model loading, input/provenance validation and
Pareto ranking are outside that enumeration budget. A geometry call is not
preempted. Product completeness refers only to the **retained finite candidate
sets**, never to all IK solutions or all task configurations. With a truncated
search, recommendations/Pareto membership apply only to evaluated candidates.

Output has `artifact_type: offline_goal_selection`, `executable: false`, full
input model/configuration binding and a SHA256 of the source file. `combinations`
is the shortlist; `evaluated_combinations` contains every valid checked endpoint.
`recommended_id`, `policy_winners`, `pareto`, `selection_reasons` and `search`
explain the choices. Rejected combinations are counted by first failing layer:
pair reserve or full scene. No valid result means no solution was found within
this finite search; it does not prove task infeasibility. CLI exit2 denotes no
valid endpoint or a usage error.

## Demonstrated result, 2026-11-17

All4,096 combinations evaluated:2,192 valid,1,456 rejected by pair reserves,
448 rejected by the full-scene check.28 Pareto candidates,3 shortlisted.
Enumeration1.72s and including ranking1.87s in this one local run, excluding
model loading and provenance validation. This is not a general runtime claim.

| Representative | Summed displacement [rad] | Minimum arm gap [mm] | Joint-limit reserve [%] |
|---|---:|---:|---:|
| Least displacement — default | 1.173 | 317.1 | 17.6 |
| Largest arm clearance | 8.556 | 671.7 | 20.8 |
| Largest joint-limit reserve | 21.297 | 380.9 | 26.0 |

The larger-displacement choices illustrate why clearance alone is not the
default. They are valid endpoints, not recommendations to execute a long joint
rotation. The previous historical90cm example is also completely evaluated:
[historical viewer](../../../setup/research/offline-goal-selection-20261117/viewer-historical.html).
All4,096 combinations there passed; all three policies agree on one endpoint.

Next: generate smooth primitive-based individual paths to these targets,
preserve alternatives, then coordinate timing and validate the complete result.
Concurrent moving-base trajectories remain an explicit later extension.

Validation: independent full-state brute force reproduced all4,096 endpoint
decisions, metrics and Pareto flags.81 targeted Python cases and the native
prefilter test passed. Browser checks covered38 selections in the new viewer
and48 in the original candidate view. Logs: `setup/logs/uwa-goal-selection-*`;
reference check: `task-alternatives/verify.py` and `verification.json` beside
the saved result. This is model/software evidence, not physical validation.
