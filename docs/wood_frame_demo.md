# Wood frame assembly demo

Two arms pick up a timber crossbar and place it across the front faces of two
uprights. The third arm moves towards its approach pose during the shared
carry. It simulates two screw cycles per upright, then withdraws. The grippers
open only after the assembly has been fixed in the selected environment.

## Browser

From the cell repository, use a fresh output directory for each run.

```bash
source scripts/env.bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 tools/wood_frame_demo.py \
  --case nominal --output ../../setup/tasks/wood-frame-example/browser
```

Open the resulting `viewer.html`. Use **Phase** to jump to the synchronized
carry or an axial screw cycle. **Joints** frames the two connections. The
localization panel shows the synthetic camera views and the measured edges.
The sealed `plan.json` contains the recipe, camera result, frozen holder
transforms, controller samples and the FK/collision results. The episode
records the resulting model timeline.

`--case shifted` moves the supplied crossbar by −8 mm in world X and +25 mm
in world Y, and turns it by 5°. The measured pose is recomputed from pixels.
`--case occluded` records the camera result without preparing a motion plan.
`--hydrogen` can ask Gemini 4 Hydrogen for a region of interest when the
synthetic image fit fails. The same calibrated local fit remeasures the
original pixels. An inconclusive fit returns a reason and no accepted pose.

The default simulation stock is a 600 × 89 × 38 mm crossbar and two
350 × 38 × 38 mm uprights spaced 340 mm apart on center. The crossbar's
upper edge is 40 mm below the tops. This spacing gives the driver access
with the 40 mm neighbor-arm margin. The tested layout uses the two right
arms to carry, left rear to fasten, and left front parked. A JSON file passed
to `--recipe` can override the dimensions. The plan records the effective
version 1 recipe and the layout identity.

## Gazebo

The Gazebo entry point consumes an accepted Browser `plan.json` and the
adjacent `description.urdf`. It uses a fresh Gazebo world and a private ROS
namespace on the simulation domain. The binding verifies both the model and
the reviewed controller samples.

```bash
source scripts/env.bash
source "$UWA_WS/setup/tasks/wood_frame_20261125/gazebo-overlay/local_setup.bash"
python3 tools/run_wood_frame_gazebo.py \
  --plan ../../setup/tasks/wood-frame-example/browser/plan.json \
  --output ../../setup/tasks/wood-frame-example/gazebo
```

`--stage-only` writes the Gazebo scene and controller files for inspection.
The local overlay contains the source revision that accepts the wood
`object_model` parameter. The replay targets real-time factor 1 and uses
the checked arm profile of up to 1 rad/s. The loose beam has a simulated
mass based on an assumed timber density of 500 kg/m³. The screws are
visual markers. One Gazebo fixed joint represents the finished connection.

The accepted run `setup/tasks/wood_frame_20261125/gazebo-contact-03` recorded
all four pad contacts, all four virtual fasteners and a retained crossbar
after release and retreat. The final difference from the target was 0.83 mm
and 0.39°. The run took 68.66 seconds of simulated time. The episode uses the
sealed plan in the adjacent `browser-gazebo-reference` directory.

## Real cell commissioning

The hardware stage remains pending. It requires measured stock and fixture
geometry, a calibrated screwdriver and tool envelope, manual screw staging,
and an approved way to confirm each insertion. Qualify tool engagement on a
separate sample and the common loaded transport before the reviewed assembly
run. The existing Motion Review and N100 runtime remain the execution path.
Use the existing 0.1 rad/s hardware profile. A change to the active collision
configuration requires its separate approval if needed for the tool.
