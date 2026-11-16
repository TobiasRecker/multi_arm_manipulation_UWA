# Single-UR Configuration Space Distance Field

Implemented2026-11-16 in `uwa_cell_motion`. One selected UR moves in six joint
coordinates. The other three arms, their tools and the selected gripper's
driving joint are frozen at the request's complete start state. Tables,
cameras, tools, individual factory kinematics and central calibration remain
in the scene. The first measured example uses **right_rear**.

This is an **offline/simulation research prototype**. No Gazebo physics run or
real movement was performed in this implementation. Existing hardware planners,
hardware arming and the independent collision guard are unchanged.

The shared plan validation now has a [conservative AABB prefilter](collision_prefilter.md)
and frozen-arm cache. The historical timings below predate this optimization;
the linked before/after comparison uses an identical CDF bank and trajectory.

## Relationship to the paper and code

Reference: [Li et al., RSS2024](https://arxiv.org/abs/2406.01137),
[project page](https://sites.google.com/view/cdfmp/home),
[original code at the reviewed commit](https://github.com/yimingli1998/cdf/tree/08a725718e748366c5b4da5cbc4c67e991961f0f).
Attribution and MIT license are installed under `third_party/cdf`.

The implementation follows the **nonparametric** CDF construction in sectionIII
and the scene-conditioned `2Dexamples/cdf.py` online example, extended to UR6.
It does not transplant Franka neural weights, train a neural CDF, or claim the
paper's Franka benchmark performance. The published neural model encodes a
different robot; a UR-specific data/training stage remains future work.

1. Construct a differentiable whole-arm workspace SDF from the conservative
   full-volume sphere model, frozen obstacle spheres, oriented collision-body
   boxes and floor. All three fixed robots participate, including diagonals.
   Analytic batched six-joint FK/Jacobians use the actual URDF transforms.
2. Generate contact configurations by bounded multistart **L-BFGS-B**, minimizing
   the sum of squared SDF values (algorithm1). Keep only solutions within1mm
   of the zero level and inside actual joint limits. Half the seeds span joint
   limits, half lie around the requested start/goal corridor; no planned path
   or RRT solution supplies data.
3. Store each contact configuration and its contact-link joint-prefix length.
   The CDF query is the minimum Euclidean **joint-angle distance in radians**
   to these prefixes (eq5); its gradient is the corresponding normalized
   difference (eq6), with zeros in later joints. Min fusion combines contact
   sets as in eq8. Joint limits use their bounded unwrapped coordinates; there
   is no automatic2π shortcut across UR joint/cable bounds.
4. Roll out the paper's reactive QP (eq14) with joint bounds and the logarithmic
   condition `-gradient · delta_q <= log(CDF + gamma)`. Default `gamma=0.9`,
   maximum increment0.04rad; the0.1rad log-buffer threshold is a joint-space
   quantity, not a0.1m clearance. The default virtual QP step is one unit;
   physical time is assigned later with the shared velocity/acceleration bounds.
5. Solve the resulting strictly convex diagonal QP with one linear inequality
   and box bounds directly through its scalar monotonic dual. This solves the
   same objective/constraint without generic nonlinear line-search failures.
   An independent normalized SciPy constrained optimizer verifies the solution.
6. Validate every candidate edge and the time-parametrized result against the
   **same complete MoveIt/FCL scene and guard reserves** as RRTConnect/Circular.
   Self-collisions are checked there; the CDF steering field itself models
   external static obstacles, not self-contact manifolds. A common validated
   direct connection is allowed. Detours use only CDF-QP, with no RRT guidance,
   circular tangent bias, hidden fallback or success on timeout/stagnation.

The workspace SDF in step1 is only the contact-data generator and geometric
filter. The actual CDF in step3 measures configuration distance, not a Cartesian
distance renamed to CDF. The prototype is **scene-conditioned**: moving any
frozen arm/tool invalidates its bank. It is not the paper's scene-independent
workspace-grid/neural representation yet.

Finite exact contact samples may overestimate true configuration distance;
nonzero contact residuals and geometry approximations can err either way.
Prefix/min queries are nonsmooth at switches/ties. CDF values and projections
are not collision-clearance certificates. Full-cell validation may reject a
locally attractive step, and a reactive planner can get stuck. A bank's
contact count/residual/budget, preparation timeout and checksum are recorded.
No-data never means collision-free. Model, mesh, frozen joints, tools and
reserves bind the cache; changing the selected arm's start/goal can reuse it.

## Build and run the reproducible example

From `~/UWA_ws`:

```bash
source setup/lyrical_env.bash
colcon --log-base log_lyrical build --build-base build_lyrical \
  --install-base install_lyrical --packages-select uwa_cell_motion --symlink-install
source install_lyrical/setup.bash
ros2 run uwa_cell_motion cell_cdf demo --arm right_rear --samples 1024 --seeds 3 \
  --prepare-budget 80 --output setup/research/cdf-my-first-demo
```

This is entirely offline and starts no drivers/ROS control processes. Use a
fresh output directory: previous results are preserved. The fixed suite takes
the existing `free_04`, `blocked_direct_04` and `unreachable_04` requests, with
identical start/goal/model/bounds for RRTConnect, Circular and CDF. The planning
budget is10s each. Report, scientific plot, joint/time previews, contact banks
and JSON records are written into the output directory. `animation.html` is a
standalone **model-only** sphere/box animation with play/pause, slider and orbit;
it sends no motion and does not simulate physical tracking. Open `report.html`
locally to inspect it. The browser automation host was unavailable for the
interactive viewer's GUI check; the scientific plot was visually inspected.
JavaScript syntax, finite sphere projection and play/pause/slider/reset/zoom
logic were exercised in a JavaScript VM with DOM/canvas stubs; this is not a
browser rendering check (`setup/logs/uwa-cdf-preview-js-check.json`).

To repeat planning with the exact previous contact samples, add
`--bank-directory <previous-demo-directory>`. The original preparation time is
still shown, identified as reused in `summary.json`. Reuse does not erase the
data-generation cost. Sources/provenance are retained with each bank.

## Individual requests

Use the shared request format: complete `start` including all four arms and
gripper driving joints, and a `goals` entry for **exactly one** arm. Joint goals
contain six radians. Explicit world-frame Cartesian goals use the existing
[PTP interface](four_arm_motion.md); normalize joint targets once when comparing
methods. Do not fill missing real states with nominal simulation positions.

```bash
# request.json: a complete simulation-model start plus one arm's target
ros2 run uwa_cell_motion cell_cdf prepare request.json --samples 2048 --seed 0 \
  --prepare-budget 120 --output /tmp/ur-cdf.npz
ros2 run uwa_cell_motion cell_cdf query request.json --bank /tmp/ur-cdf.npz \
  --output /tmp/cdf-query.json
ros2 run uwa_cell_motion cell_cdf plan request.json --bank /tmp/ur-cdf.npz \
  --output /tmp/cdf-plan.json
ros2 run uwa_cell_motion cell_cdf preview /tmp/cdf-plan.json --output /tmp/cdf-plan.html
```

`query` reports radians, gradient and the sampled projection's actual SDF
residual. A projection is an analysis result, not a motion command. `plan`
returns the normal timed trajectory/diagnostics and logs CDF/gradient/constraint
effects. Frozen joints are never command coordinates. Requests with more than
one selected arm and hardware `Problem` objects are rejected explicitly.

Successful outputs are compatible with the existing **simulation-only**
`cell_motion execute <plan> --output <record>` interface, after sourcing the
cell's `scripts/env.bash` and preparing its guard/current start. This path was
not executed for this work. No new hardware execute endpoint is added.

## Current evidence

Workspace artifacts:

- `setup/research/cdf-ur-comparison-v2/report.html`: final27-trial comparison,
  three task types × three seeds × three methods. All methods solve the two
  valid tasks for all seeds and reject the deliberately out-of-limits goal.
  This is **two valid tasks repeated**, not nine independent reachable problems
  and not a representative success-rate benchmark.
- CDF contact banks:63/50/57 contacts from1024 initial states per seed,
 17.65/13.15/12.14s preparation. Final blocked CDF planning0.546–0.554s,
 3.13–3.21s including final timing/checks; planned travel61.19–61.81s under
  the existing0.05rad/s simulation profile. The CDF constraint changes5–6
  increments, so this is not merely a relabeled direct shortcut.
- RRTConnect blocked planning7.28–9.01s; Circular1.21–1.28s in this small
  example. CDF preparation is additional; these numbers do not establish a
  general performance winner. A one-off request may cost more including data.
- `setup/research/cdf-ur-comparison-v1/`: original generic-SLSQP run, with two
  false infeasibility reports preserved. Replacing only the QP solver and
  reusing all three identical banks resolved them; objectives/buffers/bounds
  and final collision checks were unchanged. A dedicated regression covers
  the failed UR input.
- `setup/research/cdf-ur-v1/`: first successful blocked example retained.
  `setup/logs/uwa-cdf-build.log`, `uwa-cdf-all-tests.log`: Lyrical build and all
  motion tests, including existing simulation/hardware regressions.
  Final package result:107 passing checks(101pytest cases plus6CTest wrappers).

Next useful extensions are a larger fixed obstacle/task suite, held-out
configuration/projection accuracy checks and a physics replay before any
conclusions about execution. Scene-independent per-point training for the UR
and neural acceleration can follow once that baseline is understood. Physical
stopping qualification remains the separate hardware work package.
