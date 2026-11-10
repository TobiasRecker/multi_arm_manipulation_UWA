# UWA four-arm laboratory cell

ROS 2 **Lyrical**, Ubuntu 26.04 and **Gazebo Jetty**. This repository models
two tables carrying one UR5, one UR7e and two UR5e robots. It starts simulated
hardware by default. The layout is provisional, not a calibrated digital twin.
Separate, explicit local hardware preparation is available in the UWA Arms app.

Project context is maintained in [HANDOVER.md](HANDOVER.md): user goals,
requirements, preferences, decisions, verified results and open work.
[AGENTS.md](AGENTS.md) defines the ongoing working and documentation rules.
[ACTIVE_WORK.md](ACTIVE_WORK.md) explains task-specific status files under `work/`
for agents sharing this checkout; read active entries before editing or restarting services.

## UWA Arme: local multi-UR preparation

Open **UWA Arme** from the application menu, or run:

```bash
bash src/multi_arm_manipulation_UWA/scripts/control.sh
```

It starts in Mock mode. Select arms at the top left, start drivers, and inspect
or test the shared MATCH controllers in the Controller tab. No SSH/rsync or
mobile-platform setup. UR bringup and the existing admittance/J-PARSE algorithms
stay in the MATCH repository; this repository supplies inventory and the small UI.
Hardware readiness and program start require separate explicit actions.
Real motion activation is currently disabled pending full four-arm collision
integration. Domain 66 is separate from Gazebo 64 and OAK 65.
See [operation, architecture and current limits](docs/ur_control_gui.md).

## Build

Physical devices were reached over the PC's temporary Wi-Fi connection on
2026-11-10: `right_rear`=192.168.8.170, `right_front`=192.168.8.103,
OAK4=192.168.8.238. The separate [hardware inventory](config/hardware_inventory.yaml)
and [read-only network report](docs/hardware_network_2026-11-10.md) record the
mapping and measured latency. They do not enable hardware drivers or motion;
the Gazebo launch remains isolated. Previous wired-camera throughput results
do not describe the current Wi-Fi path.

For the first real hand-eye test, start with **right_rear only**. See the
[camera access and staged hardware procedure](docs/right_rear_hardware_first_test.md).
Robotiq documents `http://192.168.8.170:4242/current.jpg?type=color` for the latest
camera image; the read-only attempt on 2026-11-10 could not reach the controller.
The automatic calibration backend below remains simulation-only.

The workspace is expected at `~/UWA_ws`; set `UWA_WS` before sourcing the helper
if it lives elsewhere. Dependencies are declared in the package manifests.
On an existing ROS desktop installation, install the control panel and calibration dependencies:

```bash
sudo apt-get install --no-remove ros-lyrical-rqt-joint-trajectory-controller \
  ros-lyrical-moveit-py ros-lyrical-python-qt-binding python3-scipy python3-opencv
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

## RViz and desktop application

The included [RViz configuration](uwa_cell_gazebo/rviz/cell.rviz) displays the
four arms and tables in the `world` frame, with optional TF and scan reference.
To open it alongside an already running cell without restarting the simulation:

```bash
bash ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/cell.sh rviz
```

For a new terminal launch, use `ros2 launch uwa_cell_gazebo cell.launch.py rviz:=true`
after sourcing `scripts/env.bash`.

The **UWA Cell Simulation** start-menu application opens Gazebo, rqt joint
control and RViz, and automatically starts the scan-reference publisher.
Repeated clicks reuse the existing simulation, scan publisher and the
desktop-managed RViz window, restore minimized windows and bring the existing
cell windows to the front (Gazebo for normal start, RViz for the RViz/scan actions).
This does not reset the simulated robots. The desktop entry matches Gazebo's
window class; `scripts/show_cell_windows.py` activates only windows whose PIDs
belong to the cell's systemd services on the XWayland display.
Right-click the app for **RViz öffnen** and
**Punktewolke anzeigen**, or **Simulation beenden**. The stop action also closes
the separately managed RViz window and scan publisher. Closing RViz alone
leaves the simulation running.

The default RViz tool is **Move Camera**: left-drag rotates the orbit camera,
the mouse wheel zooms, and middle-drag pans. The **Views** panel exposes the
orbit distance and focal point as well. These tools are explicitly included in
the configuration; loading a file without a `Tools` section clears RViz's tools.

Install or refresh the menu entry for the current user, without sudo:

```bash
python3 ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/install_desktop.py
```

The installer copies the entry to `$XDG_DATA_HOME/applications/uwa-cell.desktop`
and the icon to `$XDG_DATA_HOME/icons/uwa-cell-<content-hash>.png` (default data directory:
`~/.local/share`). The content hash refreshes the desktop's cached icon after
image edits. Reinstall after moving this repository. Desktop launch errors
are recorded in `~/UWA_ws/setup/logs/uwa-cell-app.log`; RViz logs are available
with `journalctl --user -u uwa-cell-rviz`.

The [application icon](assets/uwa-cell.png) was generated with the built-in
Imagegen tool; its complete [generation prompt](assets/icon-prompt.txt) is kept
with the asset.

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

Base yaw follows the user's approximate cable bearings (2026-11-06), anchored
to a −90° correction of the initial front-left mounting orientation:

| Robot | Approximate cable direction in the default layout | `base_link` yaw |
|---|---|---|
| `left_front` | Toward the operator / front (−Y) | 0° |
| `left_rear` | Rear (+Y) | 180° |
| `right_front` | Left, toward the centre (−X) | −90° |
| `right_rear` | Right (+X) | +90° |

These are mounting estimates pending calibration. `mount_rpy` specifies
the **URDF `base_link`** pose, not the teach-pendant `base` frame. Official UR
descriptions include a 180° rotation between those two frames; convert measured
extrinsics accordingly. `kinematics_file` optionally selects each physical
robot's factory-calibrated kinematics YAML. Relative paths are resolved relative
to the layout file. Neither robot IPs nor hardware drivers belong in this launch.

The installed UR description provides an explicit UR7e configuration; its
visual meshes are shared with UR5e upstream. The selected kinematic, physical
and joint-limit parameters still come from the UR7e configuration.

## Static OAK4 overview camera

The OAK4-D is modelled on an approximate tripod to the **right** of the cell.
Its RGB optical centre starts at world **[1.8, -0.8, 2.0] m**, looking at
**[0, -0.1, 0.95] m**: right/front, about 29° downward. This respects the
user's **2 m maximum tripod height**. It is not a measured calibration.
The nominal 67.3° horizontal FOV uses a 4000×3000 pinhole RGB image at
3 Hz simulation time. [Detailed setup and design limits](docs/oak_overview.md).

It starts with new cell launches. For an already running cell, add it without
restarting the robots, then open its simulated live image:

```bash
cd ~/UWA_ws
bash src/multi_arm_manipulation_UWA/scripts/overview.sh start
bash src/multi_arm_manipulation_UWA/scripts/overview.sh view
```

Edit only `overview_camera` in the central layout (height, position, `look_at`,
resolution), then apply it **without resetting any robots**:

```bash
bash src/multi_arm_manipulation_UWA/scripts/overview.sh reload
bash src/multi_arm_manipulation_UWA/scripts/overview.sh coverage
bash src/multi_arm_manipulation_UWA/scripts/overview.sh check \
  --output ~/UWA_ws/setup/logs/uwa-oak-overview-check
```

The checker observes both boards without moving arms; actual robot poses can
occlude them. The current 2 m pose detected 12/24 left/right corners in the
checked image (reprojection RMS 0.691/0.042 px). The left board has limited
detail reserve; this does not establish real calibration accuracy. Earlier
3 m/2.6 m experiments exceed the actual tripod limit and are historical only.
Two additional OAK cameras are available for future blind-spot/detail coverage;
the first was identified over USB as **OAK-D Pro AF (RVC2)**, while the second
remains unverified. The earlier S2-FF assumption is superseded. No mounting
poses have been assigned yet.
RGB and CameraInfo topics: `/uwa_cell/oak_overview/rgb/{image_raw,camera_info}`.
TF: `world -> oak_overview_rgb_optical_frame`. The supplied RViz config includes
the housing/tripod and frustum markers; a previously opened RViz can add a
MarkerArray display on `/uwa_cell/oak_overview/markers`.

This camera is independent of the physical Ethernet OAK. The tripod is currently
visual-only and is not an obstacle in the hand-eye MoveIt planning scene.
The [static-camera calibration proposal](docs/static_camera_calibration_plan.md)
describes reference boards, camera registration, joint refinement and validation;
it is a proposed workflow, not an implemented hardware calibration.
The clarified goal is to **measure and compensate intentional table movement**.
See the [updated table tracking concept](docs/table_tracking_calibration.md):
calibrate rigid camera mounts separately, then estimate changing table relations.

## Move the arms

Select `/uwa_cell/controller_manager` and one of the four trajectory
controllers in the **rqt Joint Trajectory Controller** window. Enable control
and adjust joint targets conservatively. This is direct joint control, not
collision-free path planning. Tables/robot links have collision geometry;
The automatic calibration below uses its own collision-checked MoveIt model.
General multi-arm coordination and real-cell synchronization are future work.

Each arm has six uniquely prefixed joints. Its native ROS action is:

```
/uwa_cell/<robot_id>_trajectory_controller/follow_joint_trajectory
```

The corresponding `joint_trajectory` topic is also available. All four arm
controllers, four gripper controllers and the common joint-state broadcaster
start active (nine controllers in total).

## Robotiq 2F-85 grippers and Wrist Cameras

Each arm now carries a **Robotiq 2F-85** and a simulated **Wrist Camera 2019**.
The reported example devices are gripper S/N C-43008 (2020) and camera
S/N Q-021114 (2019); individual serial-to-arm assignments are not established.
The camera lens is mounted **opposite the UR tool I/O connector**, on +Y of
the nominal UR `tool0` frame. Its nominal line of sight tilts 30° outward
from the tool axis. The camera adds 13.5 mm between the flange and the gripper
without an extra tool plate or a second gripper coupling.

In the existing rqt window select `/uwa_cell/controller_manager`, then
`<robot_id>_gripper_controller`. The single editor commands the driving
knuckle angle: **0 rad = open, 0.8 rad = closed**. The five other finger joints
follow through mimic coupling. Angles are not opening widths in metres.
The gripper's trajectory action is:

```
/uwa_cell/<robot_id>_gripper_controller/follow_joint_trajectory
```

For example, close the front-left gripper gradually after sourcing `scripts/env.bash`:

```bash
ros2 action send_goal \
  /uwa_cell/left_front_gripper_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  '{trajectory: {joint_names: [left_front_robotiq_85_left_knuckle_joint], points: [{positions: [0.65], time_from_start: {sec: 3}}]}}'
```

Use `positions: [0.0]` to reopen. Disable rqt's output for that controller
before sending separate action goals.

All four cameras publish **640 × 480 RGB at 10 Hz in simulation time**:

| Robot ID | Image topic | Calibration topic |
|---|---|---|
| `left_front` | `/uwa_cell/left_front/wrist_camera/image_raw` | `/uwa_cell/left_front/wrist_camera/camera_info` |
| `left_rear` | `/uwa_cell/left_rear/wrist_camera/image_raw` | `/uwa_cell/left_rear/wrist_camera/camera_info` |
| `right_front` | `/uwa_cell/right_front/wrist_camera/image_raw` | `/uwa_cell/right_front/wrist_camera/camera_info` |
| `right_rear` | `/uwa_cell/right_rear/wrist_camera/image_raw` | `/uwa_cell/right_rear/wrist_camera/camera_info` |

In RViz, add an **Image** display, select the desired image topic and set
Reliability to **Best Effort**. The frame is `<robot_id>_wrist_camera_optical_frame`
(X right, Y down, Z forward). Since 2026-11-09 the default initial arm poses
aim all four cameras at their own table's central ChArUco board.

Common settings live under `tools` in `cell_layout.yaml`. A robot's own `tools`
mapping overrides individual settings, for example:

```yaml
robots:
  left_front:
    # ... keep the robot's existing type, table and mounting settings ...
    tools:
      camera_rate: 5.0
      camera_yaw: 0.0
      gripper_initial_position: 0.0
```

Set `camera_enabled: false` or `gripper: none` to omit an individual device.
Restart after tool changes. `camera_yaw` rotates the camera around tool0 Z;
`gripper_yaw` rotates the gripper independently. Both default to zero.
Headless launches (`gui:=false`) use EGL headless rendering for the cameras;
they still require an Ogre2-compatible graphics driver.

Gripper geometry, inertias and finger kinematics use the BSD-licensed PickNik
model. The camera housing is a primitive approximation with nominal pinhole
optics, not calibrated manufacturer CAD. Adaptive contact mechanics, Robotiq
URCap vision functions, autofocus and controllable LEDs are not simulated.
The installed physics backend reports that native mimic constraints are
unsupported; `gz_ros2_control` supplies the verified position coupling instead.
This is suitable for opening/closing and vision work; force-coupled grasping
requires further physics validation.
Sources, model revision and licenses are in [THIRD_PARTY.md](THIRD_PARTY.md).

## ChArUco boards and first calibration check

Each table carries a central **7 × 5 ChArUco board** with 40 mm squares,
28 mm markers and a 20 mm white margin. Left/right use different marker IDs.
The four initial arm configurations aim the cameras at the boards.
Settings are central under `charuco` in `cell_layout.yaml`.

Print the identical physical boards using the
[A3 PDF (two pages, recommended)](output/pdf/uwa_charuco_boards_A3_1to1.pdf)
or [A4 tiled PDF (four pages)](output/pdf/uwa_charuco_boards_A4_tiled_1to1.pdf).
Each complete board is 320 × 240 mm including the white margin; it does not fit
on one A4 sheet at the original scale. Print at **100% / Actual Size**, disable
Fit to Page, and measure the 100 mm control bar and 40 mm square edge.
For A4, trim at the crop marks and align the two halves with 20 mm overlap.
Mount the result flat on a rigid backing. The optional generator is
`python3 scripts/print_charuco.py` after sourcing `scripts/env.bash`; it additionally
requires `python3-reportlab` and reads the board settings directly from the layout.

```bash
source ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 run uwa_cell_gazebo charuco_check \
  --output-dir "$UWA_WS/setup/logs/uwa-charuco-check"
```

The read-only tool detects each board with OpenCV, saves raw/annotated camera
images and a JSON report, and compares ten image-based poses per camera with
timestamp-matched simulation ground truth. It also estimates each robot base
in `left_table_top` / `right_table_top` and the relative base transform per table,
assuming known board placement, intrinsics, camera mounting and arm kinematics.
This is the first simulation check and assumes known hand-eye transforms.
The automatic routine below estimates these from multiple arm poses.
No estimated transform is applied automatically.

See [the calibration guide](docs/charuco_calibration.md) for frames, transform
equations, diagnostics and recalculating initial views after layout changes.
The [dated validation report](docs/charuco_validation_2026-11-09.json) records
the first successful four-camera check against ground truth.

## Automatic hand-eye calibration

With the cell running, open the separate Qt calibration window:

```bash
source ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 launch uwa_cell_calibration calibration.launch.py
```

Disable manual rqt trajectory output, select the robots and **Posen vorbereiten**,
then **Start**. The default is 40 distinct views per arm (32 fitting and eight
held-out validation views). **Diagonalpaare** is enabled by default: left front
and right rear work together, followed by left rear and right front. Inactive arms
park to the side first; setup/parking moves remain serial. The paired paths
use a shared start time/duration and collision checks with separated swept
envelopes, at at most 0.10 rad/s and 0.20 rad/s². Disable **Diagonalpaare** for
the previous one-arm mode without parking. Live views show board detections;
**Pause/Fortsetzen**, the red **STOPP** and a direct Gazebo pause remain accessible.
After both cohorts finish, all repositioned arms return to their measured
session-start poses along checked serial paths. A stop or error holds all
active arms and requires a new preparation; parked poses can be prepared again.

The tool estimates each unknown tool-to-camera transform and the relative
front/rear bases separately for each table. Validation and ground-truth errors
are displayed separately. **Ergebnis übernehmen** explicitly activates a
versioned profile and a separate `calibrated/` TF/planning model; Gazebo geometry
and the original ground-truth model stay unchanged. Sessions and raw images go
to `$UWA_WS/setup/calibration/`, outside this repository.

On first installation, restart the cell once to load controlled controller
deceleration on cancellation. The backend verifies these parameters before moving.
This routine is for simulation only. See the [full calibration guide](docs/automatic_handeye.md)
for quality limits, files, APIs, interruption behavior, offline fitting and tests.

## Optional scan reference

`~/GoogleDrive/UWA/UR Setup.ply` is a binary **Gaussian-splat PLY**, not a
triangle mesh. Its roughly 867,000 Gaussian centres can be displayed as a
filtered point reference, not as reconstructed photorealistic splats.

```bash
source ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/env.bash
ros2 run uwa_cell_gazebo prepare_scan
# Or use another file (quote paths containing spaces):
ros2 run uwa_cell_gazebo prepare_scan --input '/path/to/UR Setup.ply'
# Add the scan to an already running cell, without resetting any robot:
bash ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/cell.sh scan
# Or pass the same custom layout used to launch the simulation:
bash ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/cell.sh scan /path/to/layout.yaml
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
world-to-reference transform. Since 2026-11-09 the default layout contains a
**coarse visual alignment** fitted to the floor normal and both tabletop rectangles.
The original identity transform and scale 1 are superseded. The orientation was
disambiguated using the user's landmarks: a high item-profile robot cell behind
the tables (+Y) and approximately two metres of open space in front (−Y).
The fitted scan scale is about 0.9532; roll/pitch/yaw are approximately
−89.761° / +0.350° / +60.141°. See the
[dated fit report](docs/scan_alignment_2026-11-09.json).

This is **not a measured calibration**. The model's assumed 0.90 m table height
puts the fitted scan floor about 0.13 m above the model floor. The scan and model
also contain different arm poses. Neither discrepancy should be fixed by silently
changing robot mounts. The RViz display retains its **UNREGISTERED** label to
indicate that there is no calibrated registration. After editing scan settings,
restart only `uwa-cell-scan` if using the desktop-managed publisher; no reset
of the robot simulation is needed. The scan never contributes collision geometry
or changes robot poses.
A missing/unreadable scan logs an optional-reference error; Gazebo keeps running.
With `scan:=false`, the launch never accesses Google Drive.
The desktop app automatically starts the separately managed scan publisher,
including when using its **RViz öffnen** action. No extra checkbox or right-click
action is needed after starting the app. The **Punktewolke anzeigen** action
remains available for reopening the reference. A missing scan is nonfatal to
the simulation. Terminal launches still use `scan:=false` by default.
Enable the **UNREGISTERED scan reference** display if you have hidden it.
The source PLY and cached point coordinates remain unchanged; the fitted scale
and pose are applied only when publishing/displaying the reference.

### Display cleanup

Since 2026-11-09 the reference display is cropped to a **4 m spherical radius**
around the mean world position of the four robot bases (currently `[0, 0, 0.9]` m).
This is a world-space distance, independent of the RViz camera. The center follows
table/mount positions; `scan.crop_center` can override it explicitly.

`scan.exclude_boxes` contains fixed world-coordinate masks for the four robots
in the **recorded scan poses**, including their bases. Upper masks start above
the tabletops to preserve their surfaces and most flat objects. These are coarse
spatial masks, not semantic segmentation: other scan objects inside a mask are
also hidden. The masks do not follow the simulated arm poses. Review them after
changing the scan alignment or replacing the recording.

All cleanup occurs once after scaling and pose conversion, before publishing;
the raw PLY and import cache remain unchanged. The current recording goes from
200,000 cached points to **154,458 displayed points**: 27,133 outside the radius
and 18,409 in the fixed robot masks. These counts describe this recording and
configuration, not a target point count.

To disable these display filters set `scan.crop_radius: null` and
`scan.exclude_boxes: []`. Then reload only the desktop-managed reference:

```bash
systemctl --user restart uwa-cell-scan
```

## Verify

```bash
source ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/env.bash
python3 -m pytest ~/UWA_ws/src/multi_arm_manipulation_UWA/uwa_cell_gazebo/test -q
# Read-only clock, joint, controller and base-transform checks:
ros2 run uwa_cell_gazebo verify_cell
# Explicitly test a small wrist move on each arm and restore its original pose:
ros2 run uwa_cell_gazebo verify_cell --move
# Check four RGB streams, calibration, tool frames and finger coupling:
ros2 run uwa_cell_gazebo verify_tools
# Close/open each simulated gripper and restore its original position:
ros2 run uwa_cell_gazebo verify_tools --move
# Optionally save image snapshots and a JSON report:
ros2 run uwa_cell_gazebo verify_tools --images /tmp/uwa-camera-images --output /tmp/uwa-tools.json
```

The motion check requires domain 64, validates an error below 0.03 rad and
other-arm drift below 0.01 rad, and checks both fixed base transforms and the
actual Gazebo model-root pose. It is intended
for this simulated cell, not a hardware commissioning procedure.

The optional live UI check uses the installed rqt plugin, discovers all eight
trajectory controllers, selects six joint editors per arm and one per gripper,
and verifies current-position hold commands on each controller's topic:

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

Validated on 2026-11-09 with the Robotiq tools: both packages build, **24 offline
tests pass**, nine controllers are active, all four grippers close/open and
restore with correct finger coupling and no unrelated-joint drift above 0.01 rad.
All four arms also pass their wrist-action/restore check with stable cell roots.
Four RGB streams, camera calibration and optical TFs pass `verify_tools`;
the installed rqt plugin selects and publishes hold commands for all eight
trajectory controllers. EGL rendering with `gui:=false` also supplies all four
camera streams; the camera/clock bridges and server shut down cleanly on restart.
Evidence: `uwa-cell-tools-*.log` / `*.json` and
`uwa-cell-camera-images/` under the log directory above.
