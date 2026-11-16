---
name: uwa-digitize
description: Run resumable UWA object-digitization jobs from native wrist/OAK photo sets, using fixed shape recipes, explicit quality checks and candidate assets. Use for repeated object scans; complex shapes require the mesh route rather than a box approximation.
---

Use the project rules and current `work/` status. The CLI is
`bash src/multi_arm_manipulation_UWA/scripts/digitize.sh` from the workspace.
Read [the workflow](../../../docs/digitization_workflow.md) for schemas or errors,
and its student-robot section when resuming that job.

1. For an existing object, run `status --job ABSOLUTE_JOB_DIR` first. Do not
   recreate the job or repeat captures when resuming offline processing.
2. For a new object, `init` with its ID, rough dimensions in metres and family:
   `box_shell`, `plate_l`, or `multiview_mesh`. Known wall/plate/profile sizes
   are user-supplied data, not newly measured dimensions. Use the mesh family
   for articulated/open machinery; do not force a simple recipe to fit it.
3. `ingest` a complete, stationarity-confirmed set, or explicitly `capture`
   when camera use is authorized and devices are available. `capture` sends
   no robot commands. A second set needs `--new-view`; repeated static photos
   are not new viewpoints. A failed restore requires explicit `recover` first.
4. `prepare` freezes optics, native image/identity/focus checks, observed board
   poses, exclusions and coverage. Read `next_action`. Do not change calibration
   flags, thresholds, or raw manifests to make a check pass.
5. For simple recipes use image-bound `fit` landmarks with preassigned fit/
   validation roles, optional `texture` face annotations, then `export`.
   `--draft` creates a visibly unapproved candidate when residual checks fail;
   it does not grant accuracy. Use `track-check` only as a held-out-image test.
   Prefer one `run --annotations FILE --faces FILE` call for all offline stages
   once these data exist. It stops at missing inputs/failed quality, never
   captures, and needs explicit `--draft` to export a failed-fit candidate.
6. For `multiview_mesh`, inspect `prepared/reconstruction_request.json` and
   the missing-view/mask/backend request. This version has no validated dense
   mesh backend. An explicit, reviewed outer-envelope experiment can use the
   standalone CPU prototype in [student_robot_visual_hull.md](../../../docs/student_robot_visual_hull.md):
   hash-bound manually reviewed silhouettes, fixed fit/validation roles, declared
   support constraint, texture from fit images only. Its watertight GLB/STL is a
   DRAFT candidate, not reconstructed grid/interior/material or a validated
   standard backend. Keep the regular job's missing-stage/quality status honest.

Regular execution changes job data, not source code. Missing physical features,
ambiguous landmarks or unknown geometry call for focused input/development.
Summarize separate geometry, visual, tracking and manipulation states, timing,
the next useful action and artifact paths. Successful process exit alone is
not a passed quality check. Status is read without acquiring hardware.

Additional wrist views require separately checked motion plans and existing
motion supervision; `envelope` is only a planning reference. Historical starts
and successful offline paths are not current hardware authorization. If the
operator has powered the URs off, continue offline until availability is restored.
Do not start drivers, Power/Brake/Play or motion from this digitization skill.
