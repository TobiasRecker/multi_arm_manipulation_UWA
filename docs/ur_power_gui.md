# UWA Robot Power

Open **UWA Robot Power** from the Linux application menu. Opening the app only
reads the four arms; it does not switch them on or off. This is the normal
operating interface, not a test panel. Closing its window leaves the persistent
ROS drivers running. Standby stops the robot program and drives; local driver
processes can remain available for the next Start + ROS.

| Button | What happens |
| --- | --- |
| **Standby** | Stops the configured `ros.urp` if active, then switches off power to the arm drives. The control boxes, Teach Pendants and Dashboard stay online. |
| **Start + ROS** | Uses the [existing UR bringup](ur_bringup.md): reuses or starts the local ROS drivers, enables the arms, releases the brakes and starts the configured `ros.urp`. |
| **Safety log** | Shows recorded guard events, carton workflow failures and review decisions from the past 24 hours. **Refresh log** reads the sources again. **Save logs** saves a fresh snapshot on ROSmini. |

Finish the experiment before Standby; put down any load that needs powered
holding. A non-ROS program is left alone and reported. Keep the work area clear
for Start. These actions are for temporary standby, not emergency stop or
electrical isolation. The app does not send movement targets, reset stops or
shut down the control boxes.

Each arm is reported independently. **DRIVES OFF** requires Dashboard
confirmation of `POWER_OFF` and a stopped program; **ROS READY** requires
`RUNNING`, the configured program playing, and the matching ROS reverse
connection. A missing Remote Control selection or other problem is shown in that
arm's row. Read-only refreshes don't clear the last action result.

Reinstall for the current desktop user if the workspace moves:

```bash
python3 ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/install_ur_power_desktop.py
```

For agents: `scripts/ur_cell_power.py status` emits one JSON event per arm
and a final event. The explicit `standby` and `start` CLI modes act on
physical hardware, share the bringup lock, and return nonzero on an incomplete
action. They are never run by a read-only refresh or app startup.

## N100 driver host

The window runs on ROSmini in both modes. `scripts/ur_power_gui.py --n100`
uses the N100 Ethernet SSH profile to run the same Power backend and displays
**N100 driver host**. A lost SSH response reports the status as unknown until
it can be read again. Close the current application window before changing
hosts. See the [N100 setup and cutover](../../../setup/n100/ur-runtime/README.md)
for the hardware handoff and how to set the application menu to the N100.

## Investigating a stop

**Safety log** is available from either main tab. You can also right-click the
**UWA Robot Power** launcher and choose **Safety log** while another window
or review session is open. From a terminal on ROSmini the same independent
viewer opens with this command.

```bash
python3 ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/ur_power_gui.py --n100 --safety-log
```

The N100 report reads the guard journal, saved carton workflow and phase
reports, and the review database. The mock viewer reads its own review
database. Each source shows its coverage. Times are UTC. The report
distinguishes a block before a phase command, an abort after observed motion,
monitor observations and native stop requests. Repeated native requests are
grouped by arm, cause and time. An occurrence count describes recorded evidence.
Confirming physical motion requires a motion measurement.

**Save logs** writes the readable report, its structured events and the
current window's event log into a local archive under
`~/UWA_ws/setup/logs/uwa-control/exports/`. Its path is displayed and written
to `~/UWA_ws/setup/logs/uwa-control/latest-export.txt`. In the archive,
open `session/safety-report.txt` first. The JSON alongside it includes
sources, event times, available measurements and references. If the N100
is unreachable, the archive records the collection error and local session.
The independent viewer has its own local session. An already-running older
power window starts recording its GUI events the next time it is launched.
