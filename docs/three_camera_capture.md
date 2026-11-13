# Mobile-board photos with the two right wrists and OAK4

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
