# Mobile-board photos with the two right wrists and OAK4

## Automatic Gemini marker review

Every saved camera photograph in a registered **UWA Camera Capture** session
gets a background review by **Gemini 4 Hydrogen High** through Antigravity.
The camera application can keep capturing and can close while the queue works.
It also registers sessions in custom output directories. The running desktop
session that began at 14:39 AWST on 23 November 2026 was registered in place.

For each photograph OpenCV measures marker IDs and all four marker vertices,
plus interpolated ChArUco IDs and corners in original sensor pixels. Hydrogen
sees the whole field of view, a measurement overlay and image details.
It can request a second measurement on native pixels in a crop or on a
perspective-corrected board. It then chooses the evidenced pass per board and
records its visual assessment. Coordinates, source SHA-256, detector passes,
model selection and review are saved beside the set. The capture manifest
retains the original GUI observations and stationarity evidence.

Open the set's **gemini-charuco/status.json** for per-camera progress. Each
completed entry links to its **review.json**. Follow its `final_report`
filename for the selected native pixel measurements. A checked revision can
also link back to its initial review. An `uncertain` assessment means the
available evidence warrants another look. Fewer than 12 noncollinear ChArUco
corners can still identify the board while falling short of the acquisition
quality threshold. New windows show progress for the last set in English.

The ROSmini user service is `uwa-gemini-charuco.service`. Its persistent queue
is under `setup/calibration/gemini_charuco_queue/` and resumes after login or
a service restart. Temporary errors appear as `retrying`. The service uses
the existing Antigravity login. From the workspace, inspect it with
`systemctl --user status uwa-gemini-charuco.service` or read the queue with
`python3 src/multi_arm_manipulation_UWA/uwa_cell_control/uwa_cell_control/gemini_photo_queue.py --workspace "$PWD" status`.
The [Gemini instructions and toolbox](../tools/charuco_agent/GEMINI.md) describe
the output and the handling of partial boards and duplicate markers.
To reinstall the service on this workstation, use
`systemctl --user enable --now "$PWD/setup/systemd/uwa-gemini-charuco.service"`
from the workspace root.

## Six-camera acquisition, 23 November 2026

The application-menu entry now selects four wrists, Ethernet OAK4 and the
USB OAK-D Pro AF on N100. The original three/five-camera CLI modes remain
available. Start the six-camera session explicitly with:

```bash
bash src/multi_arm_manipulation_UWA/scripts/camera_capture.sh \
  --six-cameras --board mobile --telemetry-source rtde --keep-camera-settings
```

The six-camera window keeps all six native streams open. Wait for **READY**,
hold the board still and press **CAPTURE ALL SIX**. All six cameras receive
parallel requests for a new frame. **FRAMES ACQUIRED** means you can move
the board. **DONE** means the files, board observations and manifest have
been saved. The button becomes available again for the next set.

The saved originals are 2592×1944 wrist JPEGs, an 8000×6000 Ethernet OAK4
PNG and a 4056×3040 USB OAK PNG. Only the USB panel is rotated 180° for its
inverted mount. Raw pixels and detected corner coordinates use the sensor
orientation. Each wrist hands over its video device once for the session.
Both OAKs derive previews and photos from the same native stream. Use
**Release cameras** to make all six available to other applications. This or
closing the window returns each wrist to its Robotiq vision service.
**Resume cameras** opens a new streaming session.

The acquisition profile is `config/digitization/six_camera_capture.yaml`:
LF245/LR406/RF435/RR388, OAK4 107, USB112. These are acquisition settings,
not new calibration results. USB focus112 intrinsics still need independent
calibration. The N100 uses `usb_oak_board_stream.py` from the OAK repository in
`~/uwa-camera/` for continuous acquisition and `usb_oak_photo.py` for single
shots. The desktop entry selects the existing output-only RTDE observer for
the stationarity audit. It collects the settling history in advance and logs
the acquisition window with each set.

Sessions are stored under `setup/calibration/six_camera_mobile/`. Each manifest
records `frame_confirmed_after_s` for each camera and
`all_frames_received_after_s` for the last confirmation measured from the GUI
click. A confirmation means the worker has selected the new frame. File
transfer, encoding and board detection can still be underway. Exposure clocks
are independent. Add `--single-shot` to open the earlier GUI with its
temporary camera sessions and optional VGA wrist mode. The one-off CLI
`--capture-only` also uses temporary sessions.

Turn the single-sided board toward different camera pairs between sets.
Six-camera session counters accept a complete, stationary set with at least one
shared usable board pair; they do not require all six cameras to see the front
at once. Manifests retain strict `all_usable`, plus `shared_board_cameras`,
`shared_board_pairs` and `has_shared_board_pair`. Pairs must refer to the same
board ID. Detection is an acquisition aid, not a calibration quality result.

## Original three-camera mode

The **UWA Camera Capture** app is camera-only. It does not power, brake-release,
start programs or move any robot. It recognizes the **mobile A4 board** only:
DICT_4X4_100, IDs75–91, 7×5 squares of38mm, markers28mm. The fixed tableboards
do not count toward the shared-view indication.

Open **UWA Camera Capture** from the application menu, or, from `~/UWA_ws`:

```bash
bash src/multi_arm_manipulation_UWA/scripts/camera_capture.sh
```

The three images show the right-front wrist, right-rear wrist and OAK4. Wrist
previews are640×480 HTTP images with an explicit camera trigger before each
request; OAK preview is2000×1500 at2fps from the full4:3 sensor field. Preview
resolution affects corner detection. A small board can have fewer detectable
corners in a preview than in the saved native photograph. The green shared-view
banner means **at least four corners currently detected in each preview**, not
validated calibration or complete native-board coverage.

**CAPTURE ALL THREE** immediately acknowledges the click and displays elapsed
time. Hold the board still until **DONE**, including camera startup/restoration.
Photos are requested concurrently but **not exposure-synchronized**. A moving
handheld board produces incompatible observations; there is no timing correction.

Since17November the large **RECEIVED / RUNNING / DONE / FAILED** banner remains
visible above all feeds. During capture it shows elapsed seconds and the number
of photos saved. Keep holding until the banner explicitly says capture finished:
all photos saved still leaves stationarity checks and preview recovery pending.
The session counters distinguish complete saved sets, usable sets, individual
saved photos and sets needing review. A failed stationarity audit never counts
as a usable set. **LAST CAPTURE** preserves the outcome when live view resumes;
hover for full details and the saved directory. Counters cover this window's
session, not earlier sessions. Five-camera windows use more screen height.

- Default: native wrist2592×1944 MJPEG bursts (three originals, last frame selected),
  plus one native OAK8000×6000 PNG via the existing photo service.
- Quick mode: wrist640×480 HTTP JPEGs, OAK still8000×6000. Keep modes separate
  in calibration; do not reuse a VGA camera matrix for native-HD images blindly.
- The OAK uses a **single** photograph, not an HQ temporal average of a possibly
  handheld target. Its preview is closed and its shared camera lock released
  before taking the photograph; preview resumes afterwards.
- **Pause live view** releases this app's OAK device for the existing depth/photo
  tools. No foreign camera process is terminated. **Open photos** opens the session.
- Stale, paused and saved snapshot images have explicit text/age; they cannot
  satisfy the current shared-view banner. HTTP timestamps are host receipt times,
  not measured exposure times. Repeated unchanged payloads also lose current status.

For a two-camera OAK/front-wrist registration session that keeps useful settings:

```bash
bash src/multi_arm_manipulation_UWA/scripts/camera_capture.sh \
  --cameras right_front oak4 --keep-camera-settings
```

The explicit keep option records actual exit settings in
`retained_camera_settings.json` and sends no focus restoration writes. Normal
camera-service/format recovery and LED lease release still apply. The default
three-camera workflow retains its historical restoration behavior. Camera
selection includes OAK and does not access unselected wrists.

## Focus and calibration boundaries

The acquisition profile is `config/three_camera_capture.yaml`: right-front435,
right-rear388, OAK116, all manual. These are individual lens-control values, not
distances. Original wrist settings are saved before temporary changes and restored
on normal window close. Wait for an active photograph/restoration when closing;
do not forcibly kill the app. `focus_restoration.json` records actual readback.
If the app crashes, retain `original_wrist_settings.json` for explicit recovery.

Right-front435 matches the currently adopted native-HD acquisition focus. Its
calibration still has the documented below-threshold acceptance. **Right-rear
native-HD intrinsics are not yet validated at388**; its old VGA calibration is
not automatically applied. All records retain camera identity, resolution,
focus and correspondences so the appropriate per-camera calibration can be used
or fitted later. There is no solver or automatic extrinsic/profile activation here.

## Saved data

Every launch creates a session, every click a new set:

```
setup/calibration/three_camera_mobile/<session>/
  board.json
  original_wrist_settings.json
  fixed_wrist_settings.json
  preview/preview.log
  set_<time>/manifest.json
  set_<time>/{right_front,right_rear,oak4}/
    image.jpg or image.png
    annotated.jpg
    record.json
    native/<id>/...          # original wrist burst, strict restore report
  latest-set.txt
  focus_restoration.json    # on close
```

Records include SHA256, original image sizes, mobile corner IDs/pixels/object
points in metres, focus/settings, camera identity, and request/completion windows.
The manifest also retains read-only domain66 joint samples before/after capture
(including names, sample times and endpoint differences). Missing telemetry is
labelled; photos can still be useful for camera-to-camera calibration. Endpoint
agreement does not prove that an arm was stationary throughout every exposure.
OAK metadata additionally records actual device sequence/time, exposure and lens
position. Original OAK files remain under `setup/oak4/photos/`; the set contains
an independent image copy. No private pictures enter Git.

`all_captured` requires all three transactions to succeed. `all_usable` additionally
requires at least12 noncollinear native corner correspondences in every image;
`all_full` requires24/24. These are acquisition checks, not calibration validation.
Failed or partially visible sets remain saved and explicitly labelled incomplete.

For a camera-only CLI set, with automatic final focus restoration:

```bash
bash src/multi_arm_manipulation_UWA/scripts/camera_capture.sh --capture-only
```

Build/install if needed:

```bash
source setup/lyrical_env.bash
colcon --log-base log_lyrical build --build-base build_lyrical --install-base install_lyrical \
  --packages-select uwa_cell_control --symlink-install
python3 src/multi_arm_manipulation_UWA/scripts/install_camera_capture_desktop.py
```

## Explicit output-only telemetry for stationary five-camera sets

If ROS hardware drivers are not running, a camera-only five-camera set can
explicitly subscribe to actual joint positions/velocities directly:

```bash
bash src/multi_arm_manipulation_UWA/scripts/camera_capture.sh \
  --five-cameras --capture-only --telemetry-source rtde
```

ROS remains the default observer. The separate RTDE process uses protocol2,
20Hz output fields `timestamp,actual_q,actual_qd` on30004; it sends only protocol
negotiation, output setup and data-stream start. No input recipe, registers,
URScript, I/O, robot-program command or driver startup. See the
[UR RTDE protocol](https://docs.universal-robots.com/tutorials/communication-protocol-tutorials/rtde-guide.html).
Controller timestamps must advance. Existing continuous freshness, settling,
velocity and drift checks remain unchanged; missing/stale data fail the set.
This is a stationarity audit, not exposure synchronization or a motion supervisor.
Logs identify the selected source; missing ROS endpoint samples remain labelled.
The PTFE five-camera set on13.11. passed with this observer. A prior missing-ROS
attempt remains failed. Details: [PTFE asset](ptfe_l_assembly.md).

## First hardware check,2026-11-12

Both right URs supplied fresh joint states, native safety NORMAL, External Control
links present and motion controllers inactive. No robot commands were sent.
The rear HTTP image was initially overexposed; a camera-only exposure trigger
produced a usable image. Native camera restoration now corrects measured legacy
UCC1.11.1 focus-ROI/LED setter behaviour with bounded feedback and verifies every
original configuration field. Autofocus and manual-focus real transactions both
passed; old failed capture reports remain unchanged.

First full native set:
`setup/calibration/three_camera_20261112/first_sets/20261112_154033_06fc8276/set_154037_784566/`.
OAK24/24, right-rear24/24, right-front8/24: front mobile board clipped at the image
edge. All images saved successfully, but **not a complete shared calibration view**.
Reposition the mobile board within the shared field of view using the live app;
no automatic arm repositioning is part of this tool.

Installed GUI acceptance passed with real live views, a native three-camera
button capture, preview restart, pause with verified SDK lock release and final
wrist focus restoration. Evidence and screenshots:
`setup/calibration/three_camera_20261112/gui_check/20261112_154921_20ecc2ad/`.
Thirty focused automated tests passed, including stale/snapshot UI feedback,
foreign-board rejection and the delayed SDK-lock release regression.
