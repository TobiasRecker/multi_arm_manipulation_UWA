# Third-party robot models and technical references

The 2F-85 meshes in `uwa_cell_description/meshes/{visual,collision}/2f_85`
and `uwa_cell_description/urdf/robotiq_2f_85.xacro` derive from
[PickNik Robotics ros2_robotiq_gripper](https://github.com/PickNikRobotics/ros2_robotiq_gripper),
commit `a74d007d8f2f06dc6a503ad21038ba869d4999a6`, downloaded 2026-11-09.
Copyright (c) 2022 PickNik Robotics; BSD-3-Clause, reproduced in
[`LICENSES/Robotiq-BSD-3-Clause.txt`](LICENSES/Robotiq-BSD-3-Clause.txt).
The cell adaptation removes the driver's control block and the non-URDF
Gazebo Classic surface tags, and resolves mesh paths in this package.
Geometry, masses, inertias and finger kinematics retain upstream values.
The meshes include the normal and adapter assets from the same upstream folder;
the camera-mounted model does not add a separate adapter.

The Wrist Camera is a locally authored primitive approximation, based on the
[Robotiq 2019 Wrist Camera specifications](https://assets.robotiq.com/website-assets/support_documents/document/online/Vision_System_HTML5_20190116.zip/Vision_System_HTML5/Content/Vision_System-Instructions-Manual-06-2017/7.%20Specifications.htm):
13.5 mm added height and 160 g without a tool plate, optical centre
`[0, 35.7, -0.1]` mm in the UR tool frame, 30° line-of-sight tilt,
50° horizontal field of view, 640 × 480 at up to 30 fps.
The simulation defaults to 10 fps per camera. Housing shape, inertia,
distortion-free pinhole optics and mounting yaw are approximations.
This does not emulate Robotiq's proprietary vision/URCap software, autofocus,
illumination control or adaptive contact mechanics of the real gripper.

The user specifies the camera lens opposite the UR tool I/O connector.
[UR's tool-coordinate explanation](https://forum.universal-robots.com/t/base-coordinate-system-documentation/140/2)
defines +Y away from that connector. Therefore `camera_yaw: 0` places the lens
on tool0 +Y, consistently with the Robotiq drawing. Per-robot yaw overrides
remain available for different mounting configurations.

The reported hardware identifiers are 2F Adaptive 2020 S/N C-43008 and
Wrist Camera 2019 S/N Q-021114. The user confirmed the **2F-85** variant.
These identify the supplied examples, not individual assignments to all four
robots. No serial number is used to infer calibration or connect to hardware.

ChArUco board PNGs and Collada planes are generated locally from the layout
using the installed OpenCV 4.10.0 API. No external board artwork is copied.
Detection follows the modern `CharucoDetector` / `matchImagePoints` / PnP API;
see [OpenCV's ChArUco tutorial](https://docs.opencv.org/4.x/df/d4a/tutorial_charuco_detection.html)
and [solvePnP documentation](https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html).
The planar candidate is selected from image reprojection error and positive
depth, independently of simulation ground truth. Detailed frame conventions
and calibration assumptions are documented in `docs/charuco_calibration.md`.

## Supplied OAK-4-Pro CAD

The user supplied `oak4-pro-3d-model.zip` on2026-11-12, containing
`oak4 enclosure-thermal 30.STEP` (STEP header: SolidWorks2023,2024-08-06).
Derived metre-scale meshes are in `uwa_cell_description/meshes/visual/oak4_pro/`;
`provenance.json` records original/derived SHA256, tessellation, reduction,
coordinate mapping and the approximate visual anchor. The supplied archive
contains no separate license file; no additional license is asserted here.
Source CAD and conversion intermediates stay outside Git under `setup/models/`.
The tripod geometry is locally authored from primitives and does not derive
from a downloaded tripod CAD. The material palette and transparent front glass
are visualization choices. Optical extrinsics remain independent of this mesh.
