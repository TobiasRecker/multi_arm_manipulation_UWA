# RViz: simulated and measured arms together

Since2026-11-11, simulation, measured overlay and MoveIt use the
[shared measured profile](applied_calibrations.md). The rear measured arm also
has `real_right_rear_wrist_camera_optical_frame` and
`real_right_rear_measured_board_frame`. Their world location still depends on
the provisional base mount; the optical/board relation itself is measured.
An already running overlay retains its model until its own service is restarted.

The normal **UWA Cell Simulation** app now starts the existing simulated cell
and adds two measured UR overlays to its RViz configuration:

| Display | Appearance | Source |
| --- | --- | --- |
| SIMULATION - UWA cell | Original UR colours, partly transparent | Gazebo, domain64 |
| MEASURED - right front | Solid gold | 192.168.8.103 driver, domain66 |
| MEASURED - right rear | Solid cyan | 192.168.8.170 driver, domain66 |

The scene has four simulated arms plus two measured arms. Each display can be
enabled independently in RViz. If the scan makes comparison difficult, untick
the scan display temporarily; its publisher remains available. Move Camera,
Orbit and zoom retain their normal controls.

## Open it

Click **UWA Cell Simulation**, or from `~/UWA_ws`:

```bash
bash src/multi_arm_manipulation_UWA/scripts/desktop_cell.sh start
```

With the simulation already running:

```bash
bash src/multi_arm_manipulation_UWA/scripts/cell.sh rviz
```

That reuses/starts the separate read-only `uwa-cell-hardware-overlay` service.
It does not start hardware drivers, prepare robots, release brakes, play a
program or transmit a motion goal. Use **UWA Arms** for hardware preparation.
To start only the overlay: `bash src/multi_arm_manipulation_UWA/scripts/cell.sh twin`.

The direct launch also works:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 launch uwa_cell_visualization hardware_overlay.launch.py
```

Direct `ros2 launch uwa_cell_gazebo cell.launch.py rviz:=true` includes the
overlay by default; `hardware_overlay:=false` disables that inclusion. A
per-domain lock reuses an existing overlay rather than duplicating TF publishers.
Changing overlay settings requires stopping its existing service first.
Stopping the cell app also stops its visualization service, preserving the
separate hardware driver processes.

## State and timing

Only `/uwa_hardware/right_front/joint_states` and
`/uwa_hardware/right_rear/joint_states` cross from domain66 to64. The source node
has no robot command publisher, service client or action. Domain separation for
control remains intact. Simulation topics and joint values are not modified.

The twelve displayed hardware joints/frames use unique prefixes
`real_right_front_` and `real_right_rear_`. Their target topics are under
`/uwa_cell/real/<arm>/`. The six values of each complete, finite input message
drive an independent, display-only robot_state_publisher. Original hardware
messages/timestamps remain unchanged. Display copies use domain64's simulation
clock, avoiding TF mismatches between Unix timestamps and Gazebo seconds.

Each marker says **LIVE**, **WAITING** or **STALE**. Before the first complete
message, no measured robot geometry is shown. After two seconds without valid
input, that arm's geometry is hidden and the warning remains. Each arm recovers
independently. Timeout handling uses wall elapsed time, including while Gazebo
is paused. LIVE means recent ROS messages, **not** independent verification of
fresh RTDE sensor packets inside the upstream driver.

Inspect current status:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 topic echo /uwa_cell/real/status --once --qos-durability transient_local --full-length
journalctl --user -u uwa-cell-hardware-overlay -n 40 --no-pager
```

## Geometry and accuracy

Mounts follow the same `uwa_cell_description/config/cell_layout.yaml` table
poses, heights and base_link mounting poses as the virtual cell. Both real
overlays follow changes to their right-table pose after restarting the overlay.
These mounts remain estimates; **this is not a calibrated registration**.
Hardware model type and optional factory kinematics come from
`config/hardware_inventory.yaml`, independently from simulated kinematics.
Without a factory file, nominal official UR kinematics are used.

The official UR collision-shell STL meshes provide solid recolourable display
geometry; this does not add collision checking or controller plugins. The
measured overlay currently contains the six UR arm joints, without inventing
unmeasured gripper opening or wrist-camera geometry/state.

Default is superimposed comparison. For a side-by-side display, start an overlay
with a purely visual offset, for example `offset_x:=2.2`. This moves the measured
display only; it is not a physical table movement or calibration. Return offsets
to zero for the shared nominal mounting position. RViz camera placement may need
adjustment to fit the extra width. Launch also accepts `layout`, `inventory`,
`arms`, `use_sim_time`, `stale_after`, `source_domain` and `target_domain`.
The domain arguments mainly support isolated tests; production defaults are66/64.
For a custom cell layout with separate services, pass the same `layout:=...`
to `cell.sh twin`; the direct combined launch forwards its layout automatically.

## Validation, 2026-11-10

- Four offline tests: twelve unique model joints, expected nominal mount points,
  table/offset consistency, malformed/partial/nonfinite message rejection and
  hiding stale data even with a paused simulated clock.
- Combined visualization/Gazebo regression suite:61 tests passed.
- Independent domains174/175: two streams/models/world TF chains, actual input
  values, retimestamping, changing TF with a paused clock, stale hiding and
  independent recovery. Source node publishes only ROS parameter metadata;
  no robot command or simulated joint-state publisher. Report:
  `setup/logs/uwa-twin-cross-domain.json`.
- Both real streams reached LIVE. Front driver's controller list was empty;
  **only its joint_state_broadcaster** was loaded and activated to obtain angles.
  No motion controller, robot program or brake operation was started by this work.
- Running Gazebo, RViz, scan and overlay services inspected; rendered gold/cyan
  measured models alongside the simulated cell visually checked.
- Logs: `setup/logs/uwa-twin-{build,unit}.log`,
  `uwa-twin-cross-domain-{check,launch}.log`, `uwa-twin-front-broadcaster.log`,
  `uwa-twin-live-status.json`, `uwa-twin-real-acceptance.json` and `uwa-twin-rviz.png`.

This is joint-state observation and visualization. It does not synchronize
commands, execute trajectories, plan collision-free motion or establish
calibrated physical accuracy.
