# Diagnose des Exports von 14:35:45

Datum: 2026-11-10, Australia/Perth. Quelle:
`setup/logs/uwa-control/exports/20261110_143449_93931_1126aeca_1794292545896083957.tar.gz`.

## Belegt

- Aktueller Dashboardstatus im Export: hinten rechts erreichbar, NORMAL,
  Remote=true, POWER_OFF, `STOPPED ros.urp`, geladen `/programs/ros.urp`.
- ROS-Controller-Manager hinten rechts nicht erreichbar.
- Zwei Startversuche14:35:10/14:35:35 mit `already managed in this domain`
  abgelehnt. Das ist keine Dashboard-/Programmpfad-Sperre.
- Übernommenes Treiberlog: `robot_state_helper` hinten rechts13:58:59 und
  `ros2_control_node`13:59:00 mit Exitcode−11 (Segmentation Fault) beendet.
- Launch41339 lief danach mit Robot-State-Publisher, Dashboard und Stopper
  weiter. Aktuelle Prozessprüfung bestätigte fehlenden Manager/State-Helper.
  Dadurch blieb die technische Arm-Launch-Sperre belegt.

## Änderung

Nur diesen nachweislich verwaisten Launch beendet, keine echten Power-/Brake-/
Play-/Bewegungsbefehle. Vorne rechts wurde dabei nicht beendet. Ein künftiger
Manager-Exit beendet seinen zugehörigen Launch samt Hilfsprozessen und gibt die
Arm-Sperre frei. Veraltete eigene GUI-Treiberstatusdaten werden verworfen.
GUI zeigt Klickannahme, laufende Aktion, Erfolg oder Fehler persistent und
kontrastreich an; Hintergrundpolls verdrängen manuelle Fehlermeldungen nicht.

Die Ursache der nativen Segmentation Faults ist damit **nicht** behoben oder
als WLAN-Fehler nachgewiesen. Sie muss bei erneutem Auftreten getrennt mit
neuen Logs/Backtrace untersucht werden. Kein erfolgreicher realer Wiederanlauf
oder Bremsen-/Gelenkwinkeltest durch den Agenten behauptet.

Prüfungen: `setup/logs/uwa-feedback-{tests,build,live}.log`. Mock-Test für
Manager-Exit, zugehörige Prozessbereinigung und anschließenden Neustart ohne
gesperrten Arm; übrige Mock-Arme müssen erhalten bleiben. Screenshots
`setup/logs/uwa-feedback-{running,failed}.png` zeigen die sichtbare Rückmeldung.
