# Return to Home

In **UWA Robot Power → Program library → Return to Home**, select the arms
that should return. List every held object in the work area. The latest
completed joint carton lift is available under **Use recorded carton lift**.
For other objects, enter the member arms, a measured position and enclosing
geometry in the shared world frame. One group can have one to four arms.
Choose **Put down** or **Keep holding** for each object. Kept loads and their
arms stay in place and are included in the model for the other arms.

**Plan only** reads current joints from the active N100 and builds a new
plan locally. **Run recorded carton demo** uses the archived lift. Neither
mode dispatches motion or opens a gripper. **Start program** prepares a
new revision and opens the corresponding requests in **Motion review**.
Select **Return to Home** in **Task settings** to set its trust independently.
Work-area release and the shared speed selection still apply. The joint
command cap is 0.1 rad/s, with the configured TCP cap applied concurrently.

The planner uses upright translation for carrying and lowering, a stationary
opening, a straight-up withdrawal and a checked joint path to the existing
Home joint shape. Manual entry currently supports an upright enclosing box
with measured world yaw and a horizontal table support. An unsupported
object, attachment, or pose needs a suitable measured model and a new plan.

Hydrogen Low ranks the available placement and Home routes once through the existing
Antigravity session. Recurring prompts use counts and operation types.
The local planner compiles every trajectory and reports blocked phases.
A previously compiled result includes the model identity by collision
geometry, contents of the used meshes and collision exclusions. The N100
checks it again before dispatch.

## Placement and approval

Loaded movement, opening and withdrawal after a release use explicit
reviews. The first qualified loaded revision also needs the independent
Codex review of its exact digest. A local reviewer records this with
`tools/run_return_home.py --output RUN_DIRECTORY --runs RUNS_DIRECTORY
--accept-first-review PLAN_SHA256`. Use the path printed in the run evidence.
A new phase requires confirmation of the preceding result. For the opening
and withdrawal requests, inspect the fresh OAK4 photo against the proposed
placement. If the scene or the measured start changed, request a new plan.
Unloaded Home paths with only modeled structural risk can use the existing
trust-based low-risk approval.

A release onto verified support is the default. **Short drop from object
profile** requires a bound profile in
`setup/skill_library/return-home-profiles/<id>.json` and the corresponding
`<id>-evidence.json`. The profile binds the arm IDs, table, collision model
signature, `geometry_sha256` and `evidence_sha256`. The recorded carton uses
the ID `avocado-carton`. Record the qualified `position_error_m`,
`max_release_gap_m`, `landing_xy_error_m` and `upright_drop_qualified` in the
profile for a drop. The fall path and release gap including uncertainty are
checked for this revision. Every short drop is explicitly reviewed.

For multi-arm carrying, the bound profile also needs `loaded_sync` with the
measured worst `max_phase_skew_fraction`, the object's
`allowable_relative_translation_m` and `allowable_relative_rotation_rad`.
The evidence must cover the object, grip group and controller operation used.
The compiler compares the relative displacement bound against the profile
for each loaded segment. A shared command timestamp and a successful
endpoint do not measure physical synchronization.

## First carton check, 26 November 2026

The preceding run reports a successful joint 20 mm lift. The fresh N100
four-arm snapshot and the ROSmini collision model passed the portable model
comparison. The two right arms' actual joints were within the existing
0.0005 rad continuation tolerance of the lifted endpoint. The stored carton
pose spans both coplanar tables. The candidate checks the two contact
patches and the open-up withdrawal.

Hydrogen ranked the upright-then-base path first. On the measured start,
both candidate routes passed offline geometry. The upright variant returned
both right arms together and took 54.74 s of arm motion for the complete
sequence. Direct Home needed serial right-arm legs and took 74.53 s overall.
The conservative neighbor distance bound in the upright Home group was
83.5 mm. The loaded descent and open-up withdrawal are about 20 mm and
150 mm respectively. Arm times exclude approvals and gripper commands.

The actual placement uncertainty and measured loaded synchronization for
this pair are outstanding. The N100 archive has joint-lift completion and
force results, which do not bound relative progress during the descent.
The fresh OAK4 photograph shows the two arms holding the carton over the
table gap. The visible view alone gives no metric bottom-to-plate gap.
The pilot stayed offline and the grippers were left holding. Evidence is
under `setup/tasks/return_home_20261126/`.
