# Minimal hardware protection

Operator decisions, implementation and real operating transition:24November2026.
The N100 now runs `/home/rosmatch/uwa-ur-runtime/minimal-candidates/minimal.upWhPwQC`.
The desktop launcher, Safety Log and Motion Review use this same runtime.

## Active operation and physical check

`uwa-minimal-protection.service` is a permanent N100 user service, enabled for
the user default target with linger. It has `Restart=no` and no `ExecStopPost`.
It starts the collision core only. **Start + ROS** separately starts missing
drivers and the native programs; opening or closing the GUI sends no arm target.
After deliberately stopping the core, start it with
`systemctl --user start uwa-minimal-protection.service` on N100. A reboot was
not performed during commissioning; the enabled unit and its file binding were
verified. The old guard/supervisor/watchdog service is stopped.

Restart the core while idle. Controller pause latches survive a core restart,
but the core does not reconstruct their previous global pause session. If it
was restarted during a retained pause, explicitly request **SOFTWARE STOP ALL
ARMS**, inspect the acknowledgements, then **RESUME** when appropriate.

The real four-arm functional check completed two separate simultaneous wrist
tasks:0.1rad outward and back, each1.875s nominally at0.1rad/s and the existing
0.2rad/s² acceleration limit. During the first task the visible production GUI
received automated Qt mouse events for Stop and Resume. All four original
action UUIDs and paused phases were retained. Advancing actual samples over
1.036s measured a largest joint position span of0.000288rad while paused.
Both tasks completed without reset; maximum final joint error was0.000080rad.
Native programs were ready before and after; gripper registers were unchanged.

The paths passed independent four-arm progress checking and110 checks against
both host models. No physical collision or data-failure injection was performed.
This is a functional observation of these small wrist paths, not a maximum
braking-distance or long-term reliability qualification. Raw evidence and
measurement details: [operating record](../work/minimal-real-cutover-20261124.md).

## Behaviour

The UWA layer has two reasons to pause: an operator command and a geometric
collision conflict. Native UR safety and normal controller results remain
independent. Normal planned speed limits are unchanged.

| Event | Result |
|---|---|
| **SOFTWARE STOP ALL ARMS** | Pause all four arm motions. |
| Geometric collision conflict | Pause all four arm motions. |
| **RESUME** | Explicitly continue retained trajectory goals. |
| Collision state missing or older than 200 ms | Visible warning; no automatic pause. Affected body pairs are unavailable. |
| Gripper movement or registers | No UWA protection intervention. Full opening envelopes remain geometry. |
| Jog/velocity/Cartesian motion at pause | Switch that arm once to `CollisionHold`; require fresh manual input afterwards. |
| Ordinary controller/task error | Report the error; no additional all-arm/native STOP escalation. |

Pause is latched in the controller; closing the GUI or losing its connection
does not release it. A missing response is displayed as unconfirmed. A controller
acknowledgement is not presented as a measured physical standstill.

The old UWA guard, supervisor, watchdog, owner heartbeat, manager/hold polling,
standstill, measured speed, driver/native angle comparison, wrench and gripper
monitors are absent from the new execution path. The ordinary task API still
reports whether its command was accepted/completed. Motion Review and the
existing offline geometric, timing and command-limit validation remain.

The same backend is used by carton approaches/contact commands, multi-camera
Library positioning, parking, hardware camera-acquisition sequences and the
parallel five-camera scan. Their frozen paths and task speeds remain unchanged;
the multi-camera Library still visits four poses serially at 0.09 rad/s.
Old protection shell entry points reject minimal mode before creating a legacy
service or native service-exit fallback.

## Geometry and execution

`uwa_cell_protection` contains one C++ process with four output-only RTDE readers,
one cached MoveIt/FCL scene and the existing link-local sphere envelopes.
Geometry runs at 20 Hz. Models are loaded once; identical states reuse the
previous result. Collision calculation and GUI/status work are outside the
ros2_control update loop.

- Four neighbouring arm pairs retain the 40 mm sphere-envelope margin.
- FCL covers all six arm combinations, tables and self-collisions, including
  tool and camera bodies. Existing SRDF/ACM mechanical exclusions remain.
- Non-arm model coordinates are explicitly zero: these are opening-envelope
  coordinates, not fabricated gripper measurements.
- FCL runs without a live joint-limit predicate. The offline planner still
  validates its input, limits and timed paths.
- There is no new table padding, dynamic stopping envelope or reset hysteresis.
  The retained FCL contact boundary does not establish a live stop before
  table contact. Actual stopping distance remains a hardware measurement.

The JTC-derived C++ plugin keeps its original `FollowJointTrajectory` goal and
trajectory during pause. It ramps its virtual time factor to zero and back,
in addition to the native UR scaling. The installed JTC version is bound to
6.9.0; no UR driver fork is needed. New ordinary goals/topics are rejected while
paused. Existing action names are unchanged. See the
[controller implementation note](../../../setup/patches/lyrical-controllers/pausable-jtc.md).

Each controller retains its local trajectory phase. The current independent
progress checks remain applicable; this implementation does not claim exact
phase synchronization for transport of a rigid object by several arms.

## Candidate preparation

From the main workspace:

```bash
bash setup/n100/ur-runtime/stage-minimal-runtime.sh --remote
```

This creates a new `~/uwa-ur-runtime/minimal-candidates/minimal.*` directory and
verifies `SOURCE_SHA256SUMS`. It does not overwrite operative sources or start
services. `--local NEW_DIRECTORY` performs the same copy locally.

In the returned candidate directory on N100:

```bash
bash build-minimal-runtime.sh
bash protection.sh prepare-model --mode hardware --output prepared-protection
```

The default build reuses the existing runtime as an underlay and builds only
the five changed packages, sequentially at low CPU priority. Package discovery
is limited to `src/`; a candidate-root `COLCON_IGNORE` prevents a parent workspace
from discovering the archived packages. `--full` is the
separate full-source build. `UWA_MINIMAL_UNDERLAY` can select another existing
install. Neither build connects to a robot. Model preparation is file-only.

Activation requires the planned operating transition: finish current tasks,
stop the old runtime in its existing operating procedure, and start the arm
drivers from the candidate with `UWA_PROTECTION_BACKEND=minimal`. Existing
native program stop/standby remains an explicit operator operation. Both JTCs
are configured as pausable plugins; the fallback hold is loaded inactive.
Then start the single new process from the candidate:

```bash
bash protection.sh run --mode hardware --model prepared-protection/model-config.json
```

Do not run the old protection processes alongside this replacement. The new
entry has no `ExecStopPost`, native STOP fallback or restart watchdog.

On ROSmini, point the retained GUI and library at that exact candidate:

```bash
export UWA_PROTECTION_BACKEND=minimal
export UWA_MINIMAL_RUNTIME=/absolute/N100/path/to/minimal-candidates/minimal.EXAMPLE
python3 src/multi_arm_manipulation_UWA/scripts/ur_power_gui.py --n100 --protection-backend minimal
```

Power, Motion Review, the persistent protection bridge and program execution
use the same candidate root. Merely opening the GUI sends no motion command.
To bind both desktop actions persistently, use the installer on ROSmini:

```bash
python3 src/multi_arm_manipulation_UWA/scripts/install_ur_power_desktop.py \
  --n100 --minimal-runtime /absolute/N100/path/to/minimal-candidates/minimal.EXAMPLE
```

For isolated simulation-free checks use Domain 67, `LOCALHOST`, GenericSystem
and `--mode mock`. The core defaults to mock and rejects an incorrect domain.
No safety/failure tests run in Gazebo.

## Public API and checked withdrawal

In Domain 66 on N100, or Domain 67 for mock:

| Name under `/uwa_cell/protection` | Type | Purpose |
|---|---|---|
| `pause_all` | `std_srvs/srv/Trigger` | Explicit four-arm pause. |
| `resume_all` | `std_srvs/srv/Trigger` | Explicit continuation; never an automatic reset. |
| `status` | Trigger service and `std_msgs/msg/String` topic | JSON status, warnings, collision pairs and per-arm command acknowledgements. |
| `state` | `std_msgs/msg/String` topic | Shared actual arm positions, velocities and original device/receipt timestamps. |
| `begin_recovery` | `std_srvs/srv/Trigger` | Admit the exact checked withdrawal file named by `recovery_plan_path`. |

The status and state topics use reliable, transient-local depth 1. There is no
heartbeat lease or stop-on-timeout. Per-controller `pause_command` and
`pause_status` are JSON String topics. Generations are monotonic command IDs;
they do not implement a time watchdog.

`tools/minimal_recovery.py prepare` consumes a saved full start, explicit joint
targets and optional waypoints. It retains ordinary offline timing/limit checks,
checks FCL contact-free geometry, and requires every already violated neighbour
distance to increase until outside 40 mm. It refuses real FCL start contact.
The output contains the exact trajectories, dense checked states and its digest.

After reviewing that file, `execute --plan PATH --reviewed-sha256 DIGEST --output
RESULT` binds it to the C++ core. Replacement goals must be accepted while the
controllers remain paused. Resume is refused until the replacement goal SHA is
acknowledged; only then does the tool issue the explicit continuation command.
The exception is limited to those neighbour pairs and ends after leaving the
margin. It cannot disable FCL or introduce another conflicting pair.

## Verification

Evidence directory on ROSmini:
`setup/tasks/minimal-protection-20261124/`.

- `four-manager-execution.json`: two consecutive four-arm tasks through actual
  GenericSystem managers, C++ core and Python adapter; retained goal UUIDs and
  phases during pause; missing-state warning without pause; mixed velocity/JTC
  stop with no automatic restart of manual motion.
- `cpp-final-ctest.log`: all six native geometry, acceleration-ramp, API/recovery
  and actual-controller mock tests passed.
- `python-complete-tests.log`: 168 targeted Python regressions passed.
- Controller integration also checks future-start pause, long pause, new-goal
  rejection, recovery admission and cancel/new-task lifecycle at native scaling
  1.0 and 0.5.
- `collision-model-parity.json`: five archived real-cell states match the
  existing Python/FCL decisions. Maximum sphere-gap difference is
  4.44e-16 m. ROSmini checks took about 4.96–11.27 ms uncached and 0.022–0.069 ms
  for identical cached states; these are not N100 CPU or real stopping results.
- `gui-mock.png`: visible high-contrast mock GUI on the actual display.
- `n100-final-build.log`: the five-package candidate build completed successfully.
  Candidate: `/home/rosmatch/uwa-ur-runtime/minimal-candidates/minimal.upWhPwQC`.
- `n100-validation/runtime-binding.json`: JTC 6.9.0 / controller manager 6.10.1,
  all plugin/node/replay libraries resolved and Python modules from the candidate.
- `n100-cross-host-parity.json`: equal canonical collision geometry, mesh contents
  and SRDF, and identical decisions/distances for five saved states on both hosts.
  Raw model hashes contain different host file paths. N100 file checks took
  12.1–27.0 ms uncached and 0.035–0.057 ms for repeated identical states; this small
  archived sample does not establish live CPU load or stopping distance.

Hardware activation and physical stopping measurements are separate from these
software and archived-data checks.
