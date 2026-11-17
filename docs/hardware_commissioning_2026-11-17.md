# Real gripper, stop and four-arm timing checks

17 November2026, Australia/Perth. **Tests ended: all four arms held and measured
stationary; all four grippers open. No automatic reset, return or resume.**

The operator confirmed clear arm/finger travel and immediate hardware emergency
stop access. PolyScope required local safety confirmation on three arms; the
operator checked/confirmed those messages. The ordinary UR bringup was used.
No remote safety acknowledgement was sent.

## Geometry and operating limits

The new OAK photograph is in
`setup/oak4/photos/20261117-101007-standard-37a99717/`: right board24corners,
held-out RMS2.050px; left board0corners. Accordingly, the operator's explicit
fallback **0.991m rear-base spacing** was adopted in the central layout:
table X=±0.4955m. This agrees with the ruler measurement of about1.00m. Other
translations/rotations remain provisional; this is not a current6D calibration.
Existing running worlds were not moved or restarted. Old geometry-bound plans
and the90cm benchmark do not apply to the changed default. Historical benchmark
tests use their original90cm geometry without rewriting old results.

`uwa_cell_motion/config/hardware_commissioning.yaml` uses arm velocity0.003rad/s
and acceleration0.006rad/s². It preserves the40mm model reserve,10Hz checks,
200ms state freshness,1s assumed stop latency and0.2rad/s² assumed braking.
The lower motion bound yields approximately79.3mm required rear-pair clearance;
the actual-state, whole-opening finger envelope had approximately133.7mm.
Original and swept-tool full-scene checks passed the planned small motions.
Stop latency/braking remain engineering assumptions, not a qualified envelope.
The regular0.01rad/s profile was not made permissible by lowering its margins.

## Grippers

Each empty gripper was activated individually and commanded open. Final native
readback on all four: **ACT1, STA3, FLT0, PRE0, POS3, OBJ3, SPE16, FOR0**.
Rear right initially reported POS230; the other three reported POS3. These
registers confirm the open endpoint, not a calibrated aperture in millimetres
or a force in newtons. The hardware guard still covers the full opening range;
it does not silently replace its envelope with an assumed open pose.

A real protocol issue was found: an ACK to a batched POS/SPE/FOR message did
not establish matching parameter readbacks. The transport now writes FOR and
SPE individually and confirms both twice before changing POS or sending GTO.
This order matters because an already latched GTO may start motion on POS
alone. All four actual servers passed the separate-write/readback check at
the already-open target. No loaded grasp, calibrated jaw force or physical
gripper-stop qualification was performed. No automatic reset/open on errors.

## Single-arm software halt

Right-front q6 was planned for at most+0.03rad, with the slower profile. An
independent20Hz output-only RTDE stream triggered the existing per-arm
supervisor stop after measured motion. The normal full-scene-checked runner
was used; no direct unchecked joint command or artificial collision was used.

Three original records are retained:

1. Connection aborted before activation/goal due stale client discovery data.
   Connection now waits up to5s for existing health checks to pass; runtime
   freshness remains fail-fast with unchanged limits.
2. A real small movement stopped after a spurious watchdog-availability report.
   A concurrent heartbeat could arrive after a tick timestamp but before status
   publication. Witness reception now shares the supervisor lock, and the tick
   timestamp is taken after locking. A deterministic test reproduces the race;
   no heartbeat timeout was increased.
3. With that fix, the stop request, resource hold, native speed reduction and
   retained latch were recorded. The original runner still reported failure:
   its50µrad position-span criterion was below already observed stationary
   encoder noise (roughly0.08–0.11mrad across the joints).

Separate, explicit analysis of record3 confirms a quiet window of at least0.45s
with native |qd|≤0.2mrad/s, position span≤0.2mrad and fitted drift≤0.2mrad/s,
while External Control was still running. The hold/latch were active. Window
confirmation occurred **0.699s after the stop request**, including observation
time; this is not pure brake time. The original failed runner result remains
unchanged, alongside `single-stop-analysis.json`. This analysis did not change
the operational guard's standstill or clearance limits. Additional tests reject
slow drift even when reported velocity is zero and accept bounded encoder noise.

## Four-arm attempt

All arms were freshly planned for+0.03rad q6. Actual overlap was established
from four independent20Hz RTDE streams, not action-send timestamps: at least
**1.45s continuous common motion**, all four |qd6|>0.5mrad/s, receipt age≤75ms.

The target motion **did not complete**. Left-front reported0.004554rad/s against
the0.003rad/s bound. It latched first; other arms continued and subsequently
latched on their own measured speed excesses. All original failures remain
counted. This demonstrates independent stopping behavior, not a successful
full trajectory or a deliberate pair-distance-stop test.

| Measurement during observed motion | Median | p99 | Maximum |
| --- | ---: | ---: | ---: |
| Full guard callback |4.692ms|27.003ms|37.236ms|
| Geometry evaluation |4.151ms|24.359ms|32.908ms|
| Guard interval |100.005ms|101.145ms|101.355ms|

64guard samples; maximum source-receipt age at guard48.17ms. The10Hz geometry
callback had substantial compute reserve during this short test. These numbers
do not establish universal end-to-end deadlines, faster-motion suitability,
real collision reserves or hardware emergency-stop performance.

Final fresh observation confirmed all four resource holds, all four stationary
arms and maximum native joint speed0 at that sample. The protection service
remains armed with the commissioning profile. Grippers remain open; no arm
reset or return motion followed the final observation.

## Evidence and next step

Workspace `setup/research/hardware-commissioning-20261117/` contains:

- `report.html` and `real-hardware-traces.png`: visual summary.
- Native gripper activation/opening records and verified parameter readbacks.
- All three single-stop attempts and `single-stop-analysis.json`.
- Fresh starts/plans, `four-arm-execution.json`, `four-arm-measurement.json`
  and `final-held-state.json`; raw observations and failures preserved.
- `run_four_arm.py`: explicit execution/measurement harness. Do not replay old
  plans after moving arms or changing geometry/configuration.

The reusable single-arm probe is `tools/hardware_stop_probe.py`; it requires
an explicitly bound successful slow right-front plan and `--execute`, and
leaves its stop latched. It performs no power, play, gripper or reset action.

Final software verification: **153motion-package tests and24focused gripper/
read-only tests passed**. The first combined collection failed on duplicate
test-module basenames; separate package imports/importlib mode resolved that
without deleting tests or caches. Logs are
`setup/logs/uwa-live-commissioning-{motion,gripper}-regression-final.log`.
The static measurement chart was rendered and visually checked. These tests
qualify the software checks, not hardware braking or loaded manipulation.

Before attempting another complete four-arm path, investigate commanded versus
native reported velocity, especially left-front CB3. Separate a lower commanded
speed from the monitored operating bound or improve tracking, then revalidate
the trajectory and actual speed. Do not hide peaks with an unqualified filter
or weaken the stopping reserve merely to finish the test. Real hardware stop
latency/braking, pair/fault matrices and loaded carton operation remain open.
