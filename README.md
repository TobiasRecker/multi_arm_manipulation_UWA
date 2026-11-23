# UWA four-arm laboratory cell

The program library includes [OAK4 camera calibration](docs/camera_library_program.md)
as a separate camera-only program. It publishes a checked right-table reference
for twelve hours, shared with the carton program; the library displays its expiry.

**UWA Robot Power → Motion review** shows the carton pilot’s planned arm
groups, risk assessment, speed limits, RViz playback and contact photograph.
The operator can try the archived task in a local mock session. See the
[carton review and execution guide](docs/carton_motion_review.md).
The saved program `carton-supported-v1` takes the measured carton pose and arm
start as inputs. The guide includes an offline comparison for a 50 mm shift
using the same program and a mock RViz preview for each pose.
**UWA Robot Power → Program library** opens the local catalog in a browser.
The supported carton program includes an offline OAK4 registration, checked
approach and wrist-camera diagnostic. [Program library guide](docs/carton_motion_review.md#programmbibliothek-im-browser)

All four grippers now have shared ROS actions, status services and Python/CLI
helpers for opening, closing with an explicit raw-force setting and relative
opening. The persistent service defaults to monitor mode. See the
[agent guide and commands](docs/gripper_ros_api.md).

Real hardware checks on17November: all four grippers opened, a measured
single-arm software halt and actual four-arm overlap. The four-arm target
was interrupted by reported speed excess; all arms remain held. See the
[results, timing curves and remaining tracking work](docs/hardware_commissioning_2026-11-17.md).

On18November both right URs reached the carton pregrasp positions on real
hardware at the retained0.1rad/s command limit, with open grippers and confirmed
final holds. No grasp or lift was attempted. See the
[current evidence and photo](work/carton-pregrasp-20261118.md).

On19November both right arms completed the corrected supported grasp using
the N100 runtime. On the user's next request the carton was released and
both right arms returned to Home with open grippers and confirmed holds.
The user has repositioned the carton and released the work area for a new
Motion review run. All four drives are ready again, with their unloaded hold targets rebound
to current positions under stopped programs. After operator approval, right front started the reviewed high approach
and was stopped by the driver/native-state comparison. All arms are stationary,
programs stopped and right grippers open; no entry or grasp occurred.
The parallel compiler now respects the active geometric-only profile, and a
separate driver receiver preserves measurements during geometry and RPC work.
Both approach phases are prepared as shared right-arm groups, about41seconds
nominally at the retained limits. Software and passive N100 checks passed;
the new parallel revision awaits operator approval. Earlier serial aborts and
their recorded causes remain in the handover. The position-trend standstill profile is approved for future
carton runs. See the [workflow and evidence](docs/carton_supported_grasp.md).

Open **UWA Robot Power** from the application menu for all four arms.
**Safety log → Save logs** shows and exports recorded N100 guard events,
motion interruptions and review outcomes with source coverage.
**Standby** stops ROS on the robots and switches off the drives; **Start + ROS**
prepares them again. The control boxes stay online. See the
[operator guide](docs/ur_power_gui.md).

Prepare the four physical arms for ROS with the [UR bringup command](docs/ur_bringup.md).
It defaults to read-only status and reports any Teach Pendant action per arm.
Explicit `--apply` loads and starts the configured External Control program
when the robot and local driver are ready.

Native Wrist photographs now avoid a redundant format switch, with actual
V4L2 format/interval verification and fallback. With the same LED workflow:
right front18.2→15.3s, left front16.5→13.7s. LEDs follow shared photo/video use;
left-rear activation waits for its ongoing calibration to finish.
See [timings, lighting controls and rollout](docs/wrist_speed_led_2026-11-12.md).

**UWA Camera Capture** shows mobile-A4-board visibility from both right wrist
cameras and OAK4, with a single button for native photographs. Open it from the
application menu or run `bash src/multi_arm_manipulation_UWA/scripts/camera_capture.sh`.
See [three-camera acquisition, focus and saved datasets](docs/three_camera_capture.md).
The [first six-set offline evaluation](docs/three_camera_photo_evaluation_2026-11-12.md)
contains a diagnostic OAK/front-wrist pose estimate and explains the remaining
intrinsics and independent-validation limits. No calibration is activated by it.

Native **48MP Standard/HQ photographs** are available through the reusable
[OAK4 photo service](../oak_camera_calibration/OAK4_PHOTOS.md), including a CLI
and `/oak4/photo/capture_hq` (`std_srvs/srv/Trigger`, domain65). HQ uses ISO100,
longer exposure and eight averaged frames; files remain under `setup/oak4/photos/`.

The same service supports [static HQ depth snapshots](../oak_camera_calibration/OAK4_DEPTH.md):
`/oak4/depth/capture_hq` (domain65), native1280×800,16-frame robust fusion,
validity masks and original millimetre data under `setup/oak4/depth/`.
Open its camera-local 3D snapshot in RViz with
`bash src/oak_camera_calibration/tools/oak4_photo.sh view-depth`; acquisition time
is labelled and the existing cell preview remains separate.


ROS 2 **Lyrical**, Ubuntu 26.04 and **Gazebo Jetty**. This repository models
two tables carrying one UR5, one UR7e and two UR5e robots. It starts simulated
hardware by default. The layout is provisional, not a calibrated digital twin.
Separate, explicit local hardware preparation is available in the UWA Arms app.

Updated2026-11-18, the default model applies
[hardware_20261118_base_fixed_v1](docs/applied_calibrations.md).
All four measured robot base-to-board bindings, including left front, are
fixed working references by explicit user adoption. Revisit them when an
actual issue is observed. Existing wrist optics, factory kinematics and the
previous OAK registration are preserved. The newly calculated OAK pose is
saved separately as a candidate. The original nominal layout remains available.
The external camera stays world-fixed when a table moves. See
[OAK adoption, frames and renderer limits](docs/oak_preliminary_adoption_2026-11-12.md).
Named parking/capture joint references are saved without automatic execution.

A [rough real OAK pose and shared-view arm design](docs/oak_pose_and_shared_views_2026-11-12.md)
is available: experimental camera/table registration, collision-checked model
postures and a separate read-only RViz preview on domain70. These targets have
not been executed on hardware or made the simulation's default initial poses.
The subsequent [real three-arm check](docs/shared_view_hardware_2026-11-12.md)
reached all selected targets and saved native wrist-HD images with24 corners each;
left front stayed stationary. The OAK simultaneously recognized all three boards.
Camera SSH now uses persistent keys instead of repeated password prompts.

Project context is maintained in [HANDOVER.md](HANDOVER.md): user goals,
requirements, preferences, decisions, verified results and open work.
[AGENTS.md](AGENTS.md) defines the ongoing working and documentation rules.
[ACTIVE_WORK.md](ACTIVE_WORK.md) explains task-specific status files under `work/`
for agents sharing this checkout; read active entries before editing or restarting services.

## Image-to-CAD prototype

A [resumable digitization runner](docs/digitization_workflow.md) now separates
tested execution from new geometry development: native-set import/capture,
fixed optics, two parametric shape recipes, data-driven texture faces, checked
candidate export and held-out tracking checks. Use `scripts/digitize.sh`.
Complex objects explicitly request a mesh backend, which is not registered yet.
The [student robot test](docs/student_robot_digitization.md) resumed on November16:
all three checked parallel view rounds were driven with the operator at the
emergency stop. Twenty confirmed native images provide four viewpoints per wrist
and one fixed OAK viewpoint. An interrupted final capture was repeated without
motion; failure records remain intact. Camera settings are restored and LEDs off.
An initial [photo-textured silhouette model](docs/student_robot_visual_hull.md)
is now available as an unvalidated candidate; cage openings and hidden interiors
are not reconstructed. A validated dense mesh backend remains open.
Earlier camera investigations remain in the historical measurement reports;
the current fixed base-binding policy is documented above.
Actual lower-reasoning quality/latency comparison remains to be measured.

A first [assisted object-digitization pipeline](docs/object_digitization.md)
reconstructs an open three-compartment carton from saved colour photographs.
It uses a visible metric board and matching camera intrinsics, explicit image
landmarks, robust box fitting and STEP/STL/editable-SCAD export. No depth data
or robot motion. The first estimate is approximately 524×102×100 mm; wall
thickness is assumed. This is a geometric approximation, not validated metrology.

A [four-wrist plus OAK scan design and literature comparison](docs/five_camera_reconstruction.md)
describes the methods and limits. The first [OAK-first scan workflow](docs/object_scan.md)
now estimates coarse box geometry, prepares checked view proposals and provides a
five-camera viewer via `bash src/multi_arm_manipulation_UWA/scripts/object_capture.sh`.
Corner selection remains assisted; hardware progress is recorded below.
A [virtual-wall and swept-volume analysis](docs/scan_separation.md) now derives a
parallel review schedule from the unchanged scan paths. It retains the original
order for pairs without a separation proof and feeds the separate hardware runner.
A separately tested [hardware parallel runner and STOP window](docs/parallel_object_scan.md)
reached all five planned postures per robot on 2026-11-13. The verified dataset
now contains **25/25 native photographs**, with 20 wrist viewpoints and five OAK
frames. Camera work and stationarity recording run independently of the motion
guard. Following the approved OAK update to OS1.47.0,15repeated8K starts and the
final five-camera set passed; factory calibration stayed identical. All arms
are stationary, motion controllers inactive, with no automatic return motion.

The [large-carton reconstruction](docs/carton_multiview_2026-11-13.md) now exports
an open carton with visible wall cutouts and optional photo textures as STEP,
STL, GLB and editable SCAD. Approximate size404×342×163mm. Twenty photos are
used metrically; the five left-front views remain diagnostic because their
geometry is inconsistent. Held-out views retain visible residuals, so this is
a preliminary image-based model with assumed thickness, not validated metrology.

The [textured carton asset](docs/carton_scene_asset.md) is now included in
Gazebo and RViz at its reconstructed pose relative to the right board, between
the tables. It loads automatically with the cell; use `cell.sh assets` to add it
to an already running simulation. It is a static visual, with no new physics
or planning obstacle.

A first [CPU object-pose tracker](docs/object_tracking.md) now uses these textured
assets for separate static localization and fast online tracking. The bounded
real-OAK test received10fps with7.5ms median tracking computation; the object
remained stationary, so real motion/occlusion and absolute accuracy still need
validation. Start camera-only: `bash src/multi_arm_manipulation_UWA/scripts/object_tracking.sh oak`.

An isolated [FoundationPose setup on the shared TITAN RTX workstation](docs/foundationpose_titanpc.md)
now passes a100-frame recorded RGB-D motion test, with24.6ms median tracking
computation. Its own environment and caches live on a data drive; system
packages, drivers and existing environments were preserved. On2026-11-16 a real
stationary avocado-carton replay also produced visually plausible poses from
aligned OAK RGB-D and a manually annotated initial mask:1.62s registration,
18.8ms median tracking computation at640×480. Live transport, actual object
motion and independent metric accuracy remain unvalidated.


The new [PTFE L assembly asset](docs/ptfe_l_assembly.md) includes real photo
textures and STEP/STL/GLB/ROS meshes, estimated at300×177×181mm with user-supplied
10mm plates and20×20mm profiles. Five stationary camera views were captured
without arm motion. Its tracking reference is prepared, but the current CPU
texture matcher still reports LOST on this object; recognition needs further work.

## OAK camera CAD and tripod

The overview camera now uses the supplied OAK-4-Pro CAD model in **Gazebo and
RViz**, together with a locally authored telescopic tripod. The same geometry
and poses drive both views. Camera optics and the accepted preliminary pose
are preserved; the stand remains illustrative visual geometry.
See [preview, operation and verification](docs/oak_camera_cad.md).

## RViz: simulation and measured hardware together

The **UWA Cell Simulation** app now adds two measured arms to the existing
RViz scene: **right front in gold**, **right rear in cyan**, alongside the four
partly transparent simulated arms. Hardware JointState data are read from domain
66 and displayed with separate `real_` frames in domain64; no commands are bridged.
Missing/stale data are labelled and measured geometry is hidden until valid
samples arrive. Mounting poses remain provisional.

For an already running cell: `bash src/multi_arm_manipulation_UWA/scripts/cell.sh rviz`.
The read-only overlay service is started/reused automatically. See
[digital-twin view, timing and validation](docs/rviz_digital_twin.md).

## UWA Arms: local multi-UR preparation

Open **UWA Arms** from the application menu, or run:

```bash
bash src/multi_arm_manipulation_UWA/scripts/control.sh
```

It starts in Mock mode. Select arms at the top left, start drivers, and inspect
or test the shared MATCH controllers in the Controller tab. No SSH/rsync or
mobile-platform setup. UR bringup and the existing admittance/J-PARSE algorithms
stay in the MATCH repository; this repository supplies inventory and the small UI.
Hardware readiness and program start require separate explicit actions.
Manual controller operations now go directly to the driver without additional
UWA arm-count, Dashboard-state or loaded-program-path gates. Existing drivers
can be controlled from a new window. The default selection is **right_rear only**.
The app supplies no complete cell collision protection. Hardware uses domain66,
Mock uses domain67; both are separate from Gazebo64 and OAK65.
See [operation, architecture and current limits](docs/ur_control_gui.md).

For manual Cartesian motion, select one arm and open **Cartesian jog…**, or use
the application-menu action **Cartesian jog · rear right**. It uses the same
MATCH admittance/J-PARSE controller as the MuR GUI, with compliance **OFF** by
default. Hold an axis button to move; releasing it stops the jog command.
See [jogging, External Control setup and test evidence](docs/ur_jogging.md).

To prepare camera calibration, `ros2 run uwa_cell_control park_arm` can **plan**,
**preview** and separately **execute** a single-arm parking path. It reuses the
full MoveIt collision model and current joint readings; its RViz preview is
isolated on domain68. Start with [hardware parking and its current limits](docs/hardware_parking.md).

The separate `handeye_hardware` tool prepares real camera views, captures
stationary ChArUco observations, and fits intrinsics before the existing
hand-eye solver. See [hardware camera calibration](docs/hardware_handeye.md).
It now accepts all four arm IDs. The
[left-rear preparation status](docs/left_rear_calibration_preparation_2026-11-12.md)
records the completed41-view left-rear run:33 fit/8 held-out images,
intrinsics and hand-eye validation passed; versioned results are saved locally.
The left-rear result was explicitly activated globally on2026-11-12; new
model loads use bundle hardware_20261112_v3. The Gazebo backend remains separate.
The [native-HD left-rear intrinsic calibration](docs/left_rear_hd_intrinsics_2026-11-12.md)
now also passes:41 views at2592×1944/focus406,0.318px median held-out RMS.
Its recommended separate export is `left_rear_hd_20261112/result_v2/` with
k3 fixed to zero for plausible extrapolation; the original fit is preserved.
No automatic global activation or replacement of the VGA/hand-eye profile.
A separate [native-HD rear-right intrinsic calibration](docs/right_rear_hd_intrinsics_2026-11-12.md)
now passes at2592×1944/focus388:41 views,33 fit/8 held-out,0.674px median
validation RMS. The saved ROS-CameraInfo remains separate from the active
VGA404/hand-eye profile; no automatic global activation.
The first real rear-right series completed on2026-11-11:41 views,33 fitting and8
held out; intrinsics and hand-eye validation passed. Results and remaining
accuracy limits are recorded in the linked hardware calibration guide.
The subsequent [front62-view experiment](docs/front_calibration_2026-11-11.md)
completed with50 fitting and12 held-out views: intrinsics passed, hand-eye
rotation validation failed (0.652° versus0.5°), so the profile remains inactive.
Its20/33/50-view comparison showed no clear large gain from image count alone.
The [native HD40-view run](docs/front_hd_calibration_2026-11-12.md) on2026-11-12
captured all40 poses (32 fit/8 held out) at2592×1944 via the new HD service.
The intrinsic fit failed the existing1px limit (1.198px); hand-eye diagnostic
validation also failed. Original data are saved. After reviewing the failure, the user explicitly
adopted the front-HD parameters in bundle `hardware_20261112_v2`; quality remains
marked below threshold. New front models use2592×1944 K/D, not the640×480 HTTP mode.
Diagonal hardware arms now operate independently under the user's reach statement,
with all remaining collision and native UR safety checks retained.
Native HD capture was also tested on [both rear cameras](docs/wrist_hd_other_arms_2026-11-12.md):
left rear passed a complete ROS burst with restored settings and24 ChArUco corners.
Right rear supplied native images; its old UCC1.11.1 autofocus mode changes the
focus window on restart and is declined before further mode changes.

The interface, tooltips and application-menu entry are in English. Click
feedback uses a persistent high-contrast RECEIVED/RUNNING/DONE/FAILED panel,
elapsed time and detailed errors; background polling does not hide failures.
Buttons visibly highlight for 1.2 seconds after a click. Click
**Save logs** at any time to write a local diagnostic archive to
`~/UWA_ws/setup/logs/uwa-control/exports/`. The saved path appears in the GUI;
`setup/logs/uwa-control/latest-export.txt` points to the latest completed archive.
It includes this window's full log, subprocess output, related ROS logs,
controller/status context and a screenshot. Export runs in the background and
sends no robot commands. Session files persist under `setup/logs/uwa-control/sessions/`.

## Build

The robot network uses **Ethernet** after the cable replacement on2026-11-10:
PC192.168.8.209 on enp87s0, right_rear192.168.8.170, right_front192.168.8.103,
left_rear192.168.8.169 (GUI/real driver and factory kinematics checked2026-11-11),
OAK4192.168.8.238. See the [hardware inventory](config/hardware_inventory.yaml).
The initial [network report](docs/hardware_network_2026-11-10.md) is historical;
its measurements do not certify current wired throughput or latency.

For the first real hand-eye test, start with **right_rear only**. See the
[camera access and staged hardware procedure](docs/right_rear_hardware_first_test.md).
Robotiq documents `http://192.168.8.170:4242/current.jpg?type=color` for the latest
camera image; the read-only attempt on 2026-11-10 could not reach the controller.
Later the same day, a repeat read succeeded: the HTTP JPEG was **640×480**, while
the 2019 camera specification lists up to 2560×1920 at 2 fps. See the linked guide
for focus controls and the distinction between sensor and HTTP image resolution.
The subsequent [UCC1.11.3 archive analysis](docs/wrist_urcap_analysis_2026-11-10.md)
identified internal HTTP focus controls and verified both read-only settings
queries on right_rear without SSH. Focus writes and the real Qt window have
since been tested on right_rear.
Open the [camera preview/focus window](docs/wrist_camera_focus.md) with
`source scripts/control_env.bash` (from this repository), then
`ros2 run uwa_cell_control wrist_camera_gui`. It provides manual focus,
autofocus, JPEG+settings saving and restoration of the opening focus mode;
it sends no robot-motion commands. HTTP images remain640×480.
The same window now provides exposure time in microseconds, gain, Auto exposure
with EV correction and LED controls. The [native-resolution attempt and verified
brightness tests](docs/wrist_resolution_exposure_2026-11-10.md) record the limits:
no full-resolution photo was obtained in that earlier attempt; the user's manual focus was restored.
The [subsequent UCC4.1.0 archive comparison](docs/wrist_ucc4_analysis_2026-11-10.md)
confirms an internal HD capture path, but no verified simple full-resolution
download or reason to upgrade yet. The archive was not installed during that analysis on2026-11-10.
The later [real HD-module probe](docs/wrist_hd_probe_2026-11-10.md) accepted module
creation but rejected processing; no native HD image was obtained. User settings
were restored and the camera window reopened. The experimental probe is not a
working full-resolution capture command.
On2026-11-11 the user reported a camera URCap update followed by “Vision system
down”. The [USB backup and recovery notes](docs/wrist_usb_recovery_2026-11-11.md)
record the verified original stick image and matching4.1.0/VSL2.0.0 files now
written to the USB root. All303 package files passed SHA256 readback after
remounting; the stick was safely unmounted. The user subsequently confirmed
that the recovery worked.
On2026-11-12 a [native5MP front-camera photo](docs/wrist_native_photo_2026-11-12.md)
was obtained through authorized SSH and direct V4L2 capture: **2592×1944**, with
JPEG decoding and checksum verified. This briefly stops only the Vision service;
normal preview and original settings were restored. The direct JPEG has a green
cast; color quality remains separate. A [ROS HD capture service](docs/wrist_hd_service.md)
now supplies three native frames per request and integrates with the hardware
calibration CLI via `--camera-source wrist_hd_service`. A real front-camera
request passed with24 detected corners per frame and restored settings; the
new full HD calibration sequence has not yet been run. Existing VGA intrinsics
do not automatically calibrate this mode.
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

[Real carton commissioning preparation](docs/carton_hardware_commissioning.md)
now includes shared ROS Robotiq services/actions, native observations and two
successful real empty partial-travel tests. A factory-model-checked path to the
carton pregrasp is saved as offline evidence. Physical alignment and coupled
loaded execution remain open; no carton has been gripped or lifted on hardware.

The [modular manipulation harness](docs/manipulation_pipeline.md) adds versioned
skills, agent review points and an opt-in physical-contact carton scene. After
grasping, the carrying arms follow one rigid object's motion on a common time
law. Its isolated validation world does not restart this cell. Development and
actual grasp evidence are recorded separately in HANDOVER; software availability
alone is not a successful physical-contact lift.
The [programming-pipeline and demonstration review](docs/programming_pipeline_lbd_review_2026-11-17.md)
maps this foundation to task programs inferred from language and a few
demonstrations, with primary literature, recording requirements and a proposed
pilot. It is a design review; the generic task interpreter and multimodal
demonstration recorder are not implemented yet.
The follow-up [interactive and lifelong Code-as-Policy design](docs/interactive_code_policy_learning.md)
focuses on two holding arms plus a working arm, simulation review/teleoperation
corrections, and improvements from repeated execution. Collision-planner
datasets are a separate research track. The first [cooperative drawing pilot](docs/box_drawing_pilot.md)
executes a saved Python policy against a file-only three-arm kinematic model,
with episode history and phase-scoped user feedback. Physical contact, force
sensing and teleoperation takeover remain subsequent integration work.
For an independent agent trial, use the [short handoff](docs/agent_trials/BOX_DRAWING_HANDOFF.md),
[away-face prompt](docs/agent_trials/PROMPT_AWAY_FACE.md) and
[development trace protocol](docs/agent_trials/TRACE_PROTOCOL.md). The standalone
`tools/agent_trial.py` records stage times, commands, raw outputs and retained failures.
The first [completed trial review](docs/agent_trials/REVIEW_AWAY_FACE_2026-11-18.md)
confirms three model circles, identifies the search and logging bottlenecks,
and adds explicit stdin capture for reproducible editing commands.
The [second trial](docs/agent_trials/GEMINI_TRIAL_02.md) prepares a fresh Gemini
session with a new circle radius and a check of the stated grasp geometry.
The [Nikolaus house trial](docs/agent_trials/NIKOLAUS_TRIAL_03.md) adds a new
stroke in a separate checkout and checks its shape from joint trajectories.
The [fourth Gemini trial](docs/agent_trials/HOUSE_DRILL_TRIAL_04.md) extends
the task with an axial hole pattern and a trace driven by workpiece motion.
New Gemini trials start in a separate checkout with Hydrogen High by default.
The [trace protocol](docs/agent_trials/TRACE_PROTOCOL.md#abschluss-und-rückgabe)
describes the combined verification and delivery step for each task.
The latest [500g force and speed tests](docs/carton_dynamic_validation_2026-11-16.md)
include two complete10mm/s Home cycles and three loaded stop cases with retained
grip using exactly the same version-bound profile. The report preserves earlier
profiles and failures. Direct force-reference checks pass. The
default remains the historical slow experimental profile; no hardware speed
or physical maximum is qualified by these simulations.

An optional [90° carton-roll recipe](docs/manipulation_pipeline.md#experimental-longitudinal-quarter-turn-2026-11-16)
reuses the same object-led pipeline for sideways placement facing OAK. It remains
experimental; translation-only contact results do not qualify this new motion.

The [matched 1×/5× contact-force comparison](docs/carton_speed_comparison_2026-11-17.md)
completes a 147.8 mm vertical lift and return at fivefold carrying speed, with
small per-jaw load changes. It does not qualify the full quarter turn; its
configured stopping reserve rejects that complete path at 5×.

The [four-arm motion guide](docs/four_arm_motion.md) covers offline
collision and joint-limit checks, RRTConnect and a circular-field baseline.
Gazebo plays the timed plans through its normal controllers. The separate
[hardware backend](docs/four_arm_hardware_motion.md) has its own guard,
supervisor, native STOP fallback and ROS domain.

A first [single-UR CDF prototype](docs/single_ur_cdf.md) now constructs
nonparametric contact-template distances in joint radians and plans with a
paper-style reactive QP. One UR moves, the other three are frozen obstacles.
The offline demo includes RRT/Circular comparisons and a standalone motion
preview; neural training and physical execution are separate future steps.
Shared planning checks now use an [arm-AABB prefilter and frozen-arm cache](docs/collision_prefilter.md)
to avoid unnecessary fine sphere comparisons while retaining full collision validation.

The [mobile multi-arm planning survey](docs/mobile_multiarm_planning_survey_2026-11-16.md)
compares classical planning, conflict resolution, predictive optimization and
CDF/GCDF for simultaneous base and arm motion. It records the research target
of two moving tables with two arms each; the current cell model still has fixed
table-to-world joints. The survey is a research comparison, not an implemented
mobile-base planner.

A first [offline goal-candidate stage](docs/offline_goal_candidates.md) now
preserves multiple target/IK alternatives per arm and checks bounded combined
endpoints using the full cell model. `cell_goal_candidates` produces research
data, not executable trajectories. The [three-page implementation plan](output/pdf/uwa_offline_multiarm_plan_2026-11-17.pdf)
records the subsequent primitive-path and time-coordination stages.

The second stage, [joint goal selection](docs/offline_goal_selection.md), checks
the retained candidate combinations and preserves Pareto alternatives for joint
displacement, arm clearance and joint-limit reserve. `cell_goal_selection`
exports a model-bound shortlist and an inspectable comparison; paths and timing
remain subsequent work.

[Step 3 uses fixed avocado-carton corner targets](docs/offline_carton_paths.md):
four independent smooth joint transits followed by vertical120mm approaches,
with an interactive model replay. Target poses stay fixed across IK variants.
Individual paths pass sampled static/self/object checks; simultaneous starts
still violate pair reserves, so joint timing coordination remains open.

An [offline 10× trajectory-speed comparison](docs/offline_carton_speed10.md)
compresses those same paths from220.67s to22.07s. It includes derivative bounds,
unchanged-geometry checks and velocity-dependent reserve diagnostics. Its viewer
defaults to real-time playback; no physical motion was performed.

A [smoother four-arm trajectory comparison](docs/offline_carton_smoothing.md)
reduces the duration further to15.99s with almost unchanged path geometry,
lower acceleration/jerk bounds and a new sampled simultaneous collision check.
Its viewer compares both motions and plots their derivatives at real-time playback.

Smooth timing is now the default for the offline carton-approach pipeline:
`tools/plan_carton_grasp_paths.py`. The [four-side-centre test](docs/offline_carton_sides.md)
assigns one of each UR's two nearest walls, reaches all four targets in12.75s,
and passes a denser5ms sampled geometry check with53.7mm minimum arm gap.
Stopping reserves remain separate diagnostics; no physical grasp is performed.

The [diverse-start teacher](docs/teacher_start_diversity.md) searches distinct
object poses and coupled arm configurations before planning from each start.
It preserves a frozen copy of its Python sources for the offline dataset run.

The [collision-first screening experiment](docs/teacher_collision_mining.md)
now separates native contacts, envelope overlaps and clearance violations.
It exposes an unresolved arm/table collision and a missing teacher constraint;
the retained negative case is not a positive training demonstration.

The [goal-chain teacher](docs/teacher_episodes.md) adds arm/table constraints
and carries the checked state across successive goals. Two six-goal episodes
cover 1.65 m and 1.02 m of object travel, with a full-episode viewer. They expand
state coverage; a high yield of genuinely difficult references remains open.

The [3D/6D teacher dataset runner](docs/teacher_dataset_6d.md) generates a fixed
32-task pilot with family-level train/validation/test splits, validated geometric
BC transitions and a trajectory gallery. Network training remains a later step.

The [two-arm BC teacher experiment](docs/two_arm_object_teacher.md) uses the two
right arms on opposite short carton sides, with XYZ/orientation corrections,
a shared 12-joint clock and independent trajectory checks. It is offline only;
the left arms remain stationary obstacles and no BC network is trained yet.

The [four-arm object transport experiment](docs/offline_object_transport.md)
continues from that side-grasp configuration with fixed object-to-TCP transforms:
10cm lift,20cm world−X translation, lowering. The ideal path takes17.53s.
A separate gradient-based yaw experiment meets a larger mid-path clearance
demand with6.02° maximum rotation and the same centre path. Both use one shared
24-joint time law and pass sampled5ms checks; grips remain hypothetical.

Select `/uwa_cell/controller_manager` and one of the four trajectory
controllers in the **rqt Joint Trajectory Controller** window. Enable control
and adjust joint targets conservatively. This is direct joint control, not
collision-free path planning. Tables/robot links have collision geometry;
The automatic calibration below uses its own collision-checked MoveIt model.
The new motion package adds experimental multi-arm PTP coordination in
simulation and an explicit hardware backend. Physical stop/synchronization
qualification remains a separate commissioning step.

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

For the separate **robot-mounted A4 wooden board**, use the single-page
[mobile A4 PDF](output/pdf/uwa_mobile_charuco_A4_1to1.pdf): landscape,
266 ×190 mm pattern,7 ×5 squares of **38 mm**,28 mm markers, IDs75–91.
This is a different target from the40 mm table boards. Print at100% / Actual
Size and measure its100 mm reference bar before mounting. Its own
[definition and printing guide](docs/mobile_charuco_a4.md) preserve the target
geometry for the later external OAK calibration; mounting is not yet calibrated.

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
# Read the simulator clock, controller inventory and base transforms:
ros2 run uwa_cell_gazebo verify_cell
# Inspect the simulated RGB streams, calibration and tool frames:
ros2 run uwa_cell_gazebo verify_tools
# Optionally save image snapshots and a JSON report:
ros2 run uwa_cell_gazebo verify_tools --images /tmp/uwa-camera-images --output /tmp/uwa-tools.json
```

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

The [real-time preparation guide](docs/realtime_preparation.md) records the
Ubuntu26.04 kernel/privilege plan, historical simulation-guard measurements,
and passive reaction-chain measurement tools. No kernel or active hardware
profile was changed by that preparation.
