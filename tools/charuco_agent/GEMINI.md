# Review one UWA Camera Capture photograph

Your deliverable is an image-based ChArUco detection for each board requested in the frozen board definition. Use the supplied OpenCV toolbox for coordinates and the original photograph for visual verification. Keep the job's original file, frozen board and full-frame evidence intact. Each camera and image SHA-256 identifies a separate observation.

## First pass

1. Check the camera, native dimensions and SHA-256 against the job. The Ethernet OAK4 can be 8000×6000, the USB OAK 4056×3040, and the native wrists 2592×1944. Earlier sessions may contain VGA. Use the actual dimensions.
2. Inspect the original image, or its native-orientation thumbnail when the interface scales the display. The USB OAK is physically upside down. Report all image coordinates in the original sensor orientation with origin top left, horizontal coordinate right and vertical coordinate down. Convert thumbnail coordinates to native coordinates separately on each axis.
3. Inspect the full-frame evidence and overlay. In a command-capable job, produce these with the command below. The staged worker can supply the same evidence precomputed. `auto` compares native grayscale, a reduced overview and contrast-enhanced grayscale. It refines marker positions on native samples and interpolates ChArUco corners from the decoded target markers. The displayed overlay is a reduced inspection copy.
4. Check that green numbered quadrilaterals overlay actual printed markers on **the same physical board**, in the expected arrangement. Magenta crosses should land on visible checkerboard intersections. Cell geometry can hide the target in some cameras. A partial or empty observation is legitimate.

```bash
python3 detect.py --image image.png --board board.json --camera oak_usb \
  --expect-sha256 "$IMAGE_SHA256" --output full.json --overlay full.jpg
```

With an existing local UWA dataset the equivalent input is `--set /path/to/set_directory --camera oak_usb`. It reads the board definition and hash from the manifest. Both modes also work with source JPEGs.

## Target identities and evidence

Use the marker IDs, layout, dictionary, border width and legacy setting from `board.json`. Include each entry in `alternate_boards`. The mobile A4 board uses DICT_4X4_100, 7×5 squares, 38 mm squares, 28 mm markers and marker IDs 75–91. A full mobile board has 17 markers and 24 ChArUco intersections with IDs 0–23. The fixed left and right table boards typically start at marker IDs 0 and 50 and use their own geometry. The Robotiq target, packaging, robot labels and other boards can produce plausible false IDs. Keep the marker-ID and ChArUco-ID lists distinct.

The JSON contains the selected pass and per-pass counts/IDs. `markers[].corners_px` follows the encoded marker's OpenCV corner order. `charuco[].point_px` contains measured/interpolated native pixel positions with their corresponding corner IDs. The point order is independent of the display rotation. The inlier check uses a board-plane homography fitted to decoded marker quadrilaterals. It checks layout consistency in this image. Metric calibration quality, lens distortion calibration and physical pose require separate evidence.

## Recovery when the image suggests a missed board

- For a visible fragment, low contrast, conflicting passes or a duplicate ID outside the target, designate **one** ROI around the physical board including a narrow surrounding margin. Use integer `--roi X Y WIDTH HEIGHT` in raw pixels. Run again and compare both overlays. If the first report clearly matches the image and the measurements agree, keep it.
- In automatic mode the toolbox can also infer a search quadrilateral from at least three distributed decoded markers. It tries this when the pattern is incomplete and its predicted boundary fits in the image. The projected boundary guides a new OpenCV search with margin. Only decoded marker quadrilaterals and ChArUco measurements from the native image contribute to the result.
- When the printed pattern is strongly foreshortened and **four corners of its boundary can be located**, use the cyclic native pixel pairs for printed top left, top right, bottom right and bottom left. Request `--quad X0 Y0 X1 Y1 X2 Y2 X3 Y3` as the alternative to `--roi`. This rectifies discovery. The toolbox inverse-maps decoded quads, refines their corners and computes the ChArUco measurements in the original image. The boundary is a search hint and never an ID or a measured correspondence.
- Use the staged agent's structured ROI or quadrilateral request if the toolbox is hosted. In a local shell, add the region option to the example command and write separate files such as `recovery.json` and `recovery.jpg`. Use the original SHA for every pass. Keep full-frame evidence even when a crop resolves a false duplicate.
- Confirm the additional IDs and their neighborhoods in the original. Examine the projected arrangement, foreign IDs, duplicate and conflicting IDs, exclusions and rejected ChArUco intersections. A larger count alone does not establish a better pass. Choose one consistent result. Do not combine pixel lists from distinct passes, fill missing corners from a projected grid or manually assign unknown IDs.
- A single decoded target marker is weak evidence. Severe blur, occlusion, repeated IDs or inconsistent physical locations can justify a partial or ambiguous decision. If the board might be visible but the pixels do not resolve it, mark uncertainty. An empty crop cannot establish absence across the full frame.
- When two passes show complementary parts of one board, the host may offer a third verified candidate. `--fuse pass-1.json pass-2.json` verifies the image and board hashes, ordered pixel corners and centers of at least three common distributed markers, and the geometric fit of complementary IDs. It reinterpolates the ChArUco corners on the native original and checks the previously measured corners. Consider this candidate only if `fusion.boards[board_id]` is `accepted`. Inspect its overlay and retain it only when the additional measurements agree with the photograph. Let the toolbox produce the candidate; never merge pixel lists by hand.

## Return the review

Follow the caller's structured response contract. Cite the selected evidence/pass and a brief image-specific reason, including an unresolved ambiguity, search region or discrepancy when present. Copy IDs and pixel measurements from verified OpenCV evidence. Existing GUI acquisition labels may be inspected **after** your independent first pass. A usable acquisition observation follows the project's threshold of 12 noncollinear ChArUco corners; preserve unresolved conflicts separately. The hardware, photos, telemetries and calibration profiles are outside the write scope of this review.
