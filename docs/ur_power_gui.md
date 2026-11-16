# UWA Robot Power

Open **UWA Robot Power** from the Linux application menu. Opening the app only
reads the four arms; it does not switch them on or off.

| Button | What happens |
| --- | --- |
| **Standby** | Stops the configured `ros.urp` if active, then switches off power to the arm drives. The control boxes, Teach Pendants and Dashboard stay online. |
| **Start + ROS** | Uses the [existing UR bringup](ur_bringup.md): reuses or starts the local ROS drivers, enables the arms, releases the brakes and starts the configured `ros.urp`. |

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
