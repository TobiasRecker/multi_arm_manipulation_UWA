# Rear base spacing: model and board check

Update17November: a fresh image still did not yield the left board pose. The
operator explicitly accepted99.1cm as fallback; the central layout now uses
X=±0.4955m. Other mounting parameters remain provisional. The following text
records the earlier diagnostic state. See the
[subsequent real hardware checks](hardware_commissioning_2026-11-17.md).

16 November 2026, diagnostic only. No robot motion, model activation, controller
switch or change to collision thresholds occurred during this check.

The operator measured **1.00 m between the rear base mounting centers** with a
folding ruler. The grippers are open and their physical gap is approximately
0.20 m. These replace the earlier rough 0.30 m gap estimate. Measurement
uncertainty has not been established. The active model and the running normal
Gazebo description both use **0.90 m** between these bases.

At the saved actual joint positions, the original open-gripper meshes have a
gap of approximately 0.1103 m at nominal 0.90 m base spacing. Translating the
bases apart by another 0.10 m, with every other mounting parameter unchanged,
predicts approximately **0.21 m**. This is consistent with the operator's
observation; it is a conditional model calculation, not a new measurement.

Both accepted rear hand-eye files in `hardware_20261112_v3` contain measured
`T_base_board`, with base referring to **URDF base_link**, not the UR controller's
rotated base frame. Board frames use OpenCV's printed-pattern top-left origin.
For two board poses from the same calibrated OAK image:

```
T_leftBase_rightBase = T_leftBase_leftBoard
                       @ inverse(T_camera_leftBoard)
                       @ T_camera_rightBoard
                       @ inverse(T_rightBase_rightBoard)
```

The camera world pose cancels. Intrinsics/distortion, print scale, a well
conditioned image pose and unchanged board-to-base attachments still matter.
The rigid transformation includes orientation and height offsets as well as
spacing; a single ruler distance cannot establish all these components.

Applying this chain to the **saved 12 November board poses** gives **0.99115 m**
between the rear bases. This supports the ruler measurement and identifies
the nominal 0.90 m anchor as a discrepancy. It is **historical consistency**:
the old photograph did not record focus and cannot establish today's accuracy
or confirm that board attachments have remained unchanged.

Fresh camera-only acquisitions through the existing exclusive photo lease:

| Acquisition | Left table board | Right table board |
| --- | --- | --- |
| Standard, 15:46 | One marker, no ChArUco corners | 24 corners; held-out RMS 1.835 px |
| HQ, eight frames, 15:48 | One marker, no ChArUco corners | 24 corners; held-out RMS 1.924 px |

Both are native 8000×6000, same inventoried device, confirmed focus116. Full
factory rational14 distortion and native K were used. Both boards are visible,
but the distant board is visibly blurred. HQ noise reduction did not recover
its corners. The right board also exceeds the existing 1 px held-out criterion.
**No current two-board base estimate or new calibration was accepted.**

Local evidence, outside Git:

- `setup/research/four-arm-model-distance-review/board-base-review.json`:
  inputs/SHA256, image results, historical matrix, limitations.
- `review_boards.py` alongside it: offline diagnostic only, 100 randomized
  rigid-transform chain checks, no ROS/device/model writes. The image checks
  use16 fit corners and8 excluded corners when all24 are detected.
- `setup/oak4/photos/20261116-154654-standard-64b6cf69/` and
  `20261116-154841-hq-557e6abc/`: original photographs and readbacks.
- `setup/logs/uwa-four-arm-board-base-review.log`: evaluation output.

Next resolve usable two-board image geometry without moving the fixed boards,
and confirm their mounting references. Preserve this candidate separately
before updating shared anchors and rechecking all arms/tables/tools. Even at
1.00 m spacing, the present unknown-opening sphere envelope would have only
approximately0.142 m clearance, below the earlier0.173 m planning requirement.
Correcting spacing alone therefore does not establish permission to execute
the pending four-arm test. Gripper hull conservatism and stopping reserves
remain separate checks; do not lower thresholds merely to obtain a passing plan.
