# UWA four-arm laboratory cell

ROS 2 **Lyrical**, Ubuntu 26.04 and **Gazebo Jetty**. This repository models
two tables carrying one UR5, one UR7e and two UR5e robots. It starts simulated
hardware only. The layout is provisional, not a calibrated digital twin.

## Build

The workspace is expected at `~/UWA_ws`; set `UWA_WS` before sourcing the helper
if it lives elsewhere. Dependencies are declared in both package manifests.
On an existing ROS desktop installation, install the standard control panel:

```bash
sudo apt-get install --no-remove ros-lyrical-rqt-joint-trajectory-controller
cd ~/UWA_ws
source /opt/ros/lyrical/setup.bash
colcon --log-base log_lyrical build \
  --base-paths src/multi_arm_manipulation_UWA \
  --build-base build_lyrical --install-base install_lyrical --symlink-install
source src/multi_arm_manipulation_UWA/scripts/env.bash
```

For a new machine, use `rosdep install --from-paths
src/multi_arm_manipulation_UWA --ignore-src --rosdistro lyrical --skip-keys
ament_python -y` after initializing rosdep.

## Start and stop

```bash
cd ~/UWA_ws
bash src/multi_arm_manipulation_UWA/scripts/cell.sh start
bash src/multi_arm_manipulation_UWA/scripts/cell.sh status
# Stop only this cell, including its Gazebo/rqt/RViz child processes:
bash src/multi_arm_manipulation_UWA/scripts/cell.sh stop
```

Alternatively, run in the current terminal and stop with Ctrl+C:

```bash
source ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 launch uwa_cell_gazebo cell.launch.py
```

Launch arguments: `layout:=/absolute/path/layout.yaml`, `gui:=true`,
`controller_gui:=true`, `rviz:=false`, `scan:=false`.
For a headless test use `gui:=false controller_gui:=false`.
The server and GUI are separate processes to avoid the GUI world-selection
startup deadlock encountered on this machine.
The supplied Gazebo GUI configuration frames the complete cell and disables
the exit-confirmation dialog so that stopping the service closes its windows.

The cell always uses **ROS domain 64**, localhost discovery, and Gazebo
partition **`uwa_cell_sim`**. Source `scripts/env.bash` before querying or
commanding it. This is separate from the existing MuR simulation (domain 63).
The controller manager is `/uwa_cell/controller_manager`.

## Layout and calibration

Edit [`cell_layout.yaml`](uwa_cell_description/config/cell_layout.yaml), then
restart the cell. With `--symlink-install`, rebuilding for YAML edits is not
required. Alternatively pass a separate file using the `layout` launch argument.

World axes: **X right, Y rear, Z up**, origin at the floor midway between the
tables. Table poses describe floor centres. Robot mounting poses are relative
to the tabletop surface, whose frame is `<left|right>_table_top`.

| Robot ID / joint prefix | Type | Default base XYZ (m) |
|---|---|---|
| `left_front` / `left_front_` | UR5 | −0.45, −0.675, 0.90 |
| `left_rear` / `left_rear_` | UR7e | −0.45, +0.675, 0.90 |
| `right_front` / `right_front_` | UR5e | +0.45, −0.675, 0.90 |
| `right_rear` / `right_rear_` | UR5e | +0.45, +0.675, 0.90 |

Each table is 0.80 × 1.70 m. Tabletop height is provisionally 0.90 m, thickness
and leg width 0.05 m. The adjacent long edges are 0.10 m apart. Mounting centres
are 1.35 m apart along each table, leaving 0.175 m at either end.
Moving/rotating a table in YAML carries both of its robot mounts with it.

Front base yaw is provisionally +90°, rear yaw −90°. `mount_rpy` specifies
the **URDF `base_link`** pose, not the teach-pendant `base` frame. Official UR
descriptions include a 180° rotation between those two frames; convert measured
extrinsics accordingly. `kinematics_file` optionally selects each physical
robot's factory-calibrated kinematics YAML. Relative paths are resolved relative
to the layout file. Neither robot IPs nor hardware drivers belong in this launch.

The installed UR description provides an explicit UR7e configuration; its
visual meshes are shared with UR5e upstream. The selected kinematic, physical
and joint-limit parameters still come from the UR7e configuration.

## Move the arms

Select `/uwa_cell/controller_manager` and one of the four trajectory
controllers in the **rqt Joint Trajectory Controller** window. Enable control
and adjust joint targets conservatively. This is direct joint control, not
collision-free path planning. Tables/robot links have collision geometry;
MoveIt coordination and real-cell synchronization are future work.

Each arm has six uniquely prefixed joints. Its native ROS action is:

```
/uwa_cell/<robot_id>_trajectory_controller/follow_joint_trajectory
```

The corresponding `joint_trajectory` topic is also available. All four
trajectory controllers and the common joint-state broadcaster start active.

## Optional scan reference

`~/GoogleDrive/UWA/UR Setup.ply` is a binary **Gaussian-splat PLY**, not a
triangle mesh. Its roughly 867,000 Gaussian centres can be displayed as a
filtered point reference, not as reconstructed photorealistic splats.

```bash
source ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 run uwa_cell_gazebo prepare_scan
# Or use another file (quote paths containing spaces):
ros2 run uwa_cell_gazebo prepare_scan --input '/path/to/UR Setup.ply'
# Restart the service with the optional reference and RViz:
bash ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/cell.sh stop
bash ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/cell.sh start scan:=true rviz:=true
```

The importer uses position and spherical-harmonic DC colour fields, sigmoid
opacity and logarithmic Gaussian scales. It filters invalid values, opacity
below 0.1 and splat scales above 0.05, voxel-reduces at 0.01 **scan units** and
deterministically caps the result at 200,000 points. All thresholds are editable
under `scan` in the layout. Cache files live under `$XDG_CACHE_HOME/uwa_cell/scans`
(normally `~/.cache/uwa_cell/scans`), keyed by source metadata and filter settings.
Source data is read-only and is never added to this Git repository.

RViz displays `/uwa_cell/scan_reference` in the `uwa_scan_reference` frame.
`scan.scale` scales point coordinates; `scan.xyz`/`scan.rpy` set the static
world-to-reference transform. Initial settings are identity and scale 1:
**UNREGISTERED**, with no claim that scan units are metres. Changes require a
restart. The scan never contributes collision geometry or changes robot poses.
A missing/unreadable scan logs an optional-reference error; Gazebo keeps running.
With `scan:=false`, the launch never accesses Google Drive.

## Verify

```bash
source ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/env.bash
python3 -m pytest ~/UWA_ws/src/multi_arm_manipulation_UWA/uwa_cell_gazebo/test -q
# Read-only clock, joint, controller and base-transform checks:
ros2 run uwa_cell_gazebo verify_cell
# Explicitly test a small wrist move on each arm and restore its original pose:
ros2 run uwa_cell_gazebo verify_cell --move
```

The motion check requires domain 64, validates an error below 0.03 rad and
other-arm drift below 0.01 rad, and checks both fixed base transforms and the
actual Gazebo model-root pose. It is intended
for this simulated cell, not a hardware commissioning procedure.

The optional live UI check uses the installed rqt plugin, discovers all four
controllers, selects six joint editors per arm and verifies current-position
hold commands on each controller's topic:

```bash
QT_QPA_PLATFORM=offscreen python3 "$UWA_WS/src/multi_arm_manipulation_UWA/uwa_cell_gazebo/test/live_rqt_check.py"
# Three live clock-forwarding and shutdown cycles:
python3 "$UWA_WS/src/multi_arm_manipulation_UWA/uwa_cell_gazebo/test/live_clock_check.py"
```

On this Lyrical installation, the standard clock bridge crashed during library
unloading on exit. A small `clock_bridge` node uses the installed Gazebo Python
transport bindings, forwards Gazebo simulation time with ROS clock QoS, and
explicitly unsubscribes before destroying its ROS publisher. Gazebo's packaged
GUI client is launched directly so Launch can signal the window process itself.

The Gazebo GUI configuration derives from Open Robotics' Jetty default
configuration and is Apache-2.0 licensed (see `LICENSES/Apache-2.0.txt`).
The other new cell code uses this repository's MIT license.

Validated on this PC on 2026-11-06: both packages build; all 11 offline tests
pass; five controllers are active; all four arms complete and restore their
individual wrist-action test; the actual Gazebo root remains anchored. The
standard rqt plugin selects and commands all four arms. The original scan
imports as 200,000 finite reference points and a missing scan is nonfatal.
Detailed test outputs and screenshots are under `~/UWA_ws/setup/logs/uwa-cell*`.
