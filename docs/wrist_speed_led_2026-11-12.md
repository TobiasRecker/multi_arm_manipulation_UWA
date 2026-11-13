# Schnellere Wrist-Fotos und LEDs nach Kameranutzung

Nutzerauftrag vom2026-11-12: HD-Fotos ohne wesentliche Qualitätseinbußen
beschleunigen; alle vier Wrist-LEDs nur bei Foto-/Videonutzung einschalten.
Keine Armfahrt, Programm-/Bremsaktion oder Kalibrierprofilaktivierung.

## Gemessene Beschleunigung

Die bisherige native Aufnahme schaltet nach dem Dreierburst ausdrücklich von
2592×1944 auf VGA zurück. Anschließend initialisiert der Visiondienst die
Kamera erneut. Die erste Rückschaltung kostet ungefähr drei Sekunden.

Der neue Ablauf vermeidet diese doppelte Umschaltung. Nach Wiederanlauf des
Visiondiensts prüft ein unabhängiger V4L2-Aufruf **ursprüngliche Auflösung,
Pixelformat und Bildintervall** gegen den vorher gesicherten Gerätezustand.
Bei Abweichung folgen die bisherige explizite Rückschaltung, ein erneuter
Dienststart und eine erneute Prüfung. Sämtliche ursprünglichen Kamerafelder
bleiben geprüft. Kein Erfolg bei unbestätigter Wiederherstellung.

| Kamera / gleicher Lichtablauf | Bisher | Schnell | Ersparnis |
|---|---:|---:|---:|
| right_front, LED30% während Foto | 18,221s | 15,271s | 2,950s / 16,19% |
| left_front, CB3/Python2.7, LED30% | 16,522s | 13,714s | 2,808s / 17,00% |

Rechts vorne: alle sechs Vergleichsbilder mit24/24 Boardecken, native2592×1944,
Fokus435Manual/60000µs/Gain16 an beiden Burstenden aus dem Sensor gelesen.
Laplace-Schärfe bisher32,67–32,98, schnell32,79–33,06; Weiß-Clipping jeweils
etwa0,01%. Mittlere Boardecken zwischen den Bursts: RMS0,064px. Nutzer bestätigt
unveränderte Szene. Begrenzter Vergleich, kein neuer Genauigkeitsnachweis.

right_rear ebenfalls erfolgreich mit bestätigtemVGA/MJPEG und1/15s. Gesamtdauer
dort24,36s: vorhandene strenge Legacy-ROI-Wiederherstellung brauchte zusätzliche
Zeit. Keine pauschalen15s für alle Kameras versprechen. Firmwareinitialisierung
bleibt der größte Zeitblock. Native JPEGs, Dreierburst, Einlaufbilder, Frische-/
Dekodierprüfung, Sensor-Readbacks und unabhängiger Restore-Watchdog bleiben erhalten.
Eigener i686-Helfer ohne Controller-Compiler fürCB3. Originalhelfer unverändert
für eingefrorene Reihen; `NativeCapture(..., fast=False)` behält den alten Formatablauf.

## LED-Bedienung

- Erster Foto-/Video-Nutzer: Licht an, letzter Nutzer: expliziter Aus-Modus.
  Vorschauen halten Licht durchgehend; weitere Nutzer werden mitgezählt.
  Ein Snapshot allein hält kein Licht an. Fotos halten es bis zum bestätigten Restore.
- **Pause live view** gibt auch die Wrist-Beleuchtung frei. Andere Viewer dürfen
  sie weiter nutzen. Fotos im Pausenmodus sind weiterhin möglich.
- Standard für aktive Nutzung30%=53/175, bisherige von0 verschiedene Intensität
  beim erstmaligen Enrollment erhalten. Im Wrist-Fenster **LED Manual** / Prozent /
  **Apply LED**; **LED Off** setzt auch den Nutzungswert auf0. **LED Auto** wird bei
  verwalteter Beleuchtung mit verständlicher Meldung abgewiesen. Fokus/Belichtung erhalten.
- Prozessabsturz gibt Kernel-Nutzungssperren frei. `uwa-wrist-led-policy.service`
  bestätigt dann Licht0, protokolliert Fehler und versucht erneut. Im Leerlauf
  regelmäßige Prüfung. Bei Netz-/Stromverlust ist kein sofortiger LED-Befehl möglich.

Der Robotiq-Setter verwendet Modus1 für **Aus** und Modus2 für **Manuell**.
Auf UCC1.11.1, 3.44 und 4.1 meldet `forceRefresh=true` den Hardware-Schalter:
0 = aus, 1 = eingeschaltet. `lightingValue=0` allein reicht deshalb nicht als
Aus-Nachweis. Der Wächter verlangt Schalter0 und Intensität0. Bei Fokusänderung
oder Wiederherstellung nach einer Aufnahme bleiben Schalter und Intensität
erhalten. Der Wächter berücksichtigt nur aktivierte Verzeichnisse mit
gültiger IPv4-Adresse.

Erfasst sind Workspace-Clients: Wrist-Fenster, Drei-/Fünf-Kamera-App, HTTP-Fotos,
HD-Dienst und Kalibrierungsaufnahme. Fremde direkte HTTP-Clients/Pendant-Viewer
melden keine Nutzung und können durch die Leerlaufregel dunkel werden.
Eigene Videoclients mit `with camera.activity():` umschließen; einzelne
`camera.image()`-Aufrufe sind automatisch umfasst.

## Installation und Rollout

`uwa_cell_control` gebaut, keine Roboter-/Simulations-/UR-Treiberneustarts.
Benutzerdienstquelle `setup/systemd/uwa-wrist-led-policy.service`, verlinkt und
aktiviert. Originale/Profile/Status: `setup/wrist_lighting/<IP>/{profile,state}.json`.
Keine Zugangsdaten. Aktiv und real geprüft: **alle vier Wrist-Kameras**.
Der aufgeschobene left_rear-Rollout wurde am12.11. abgeschlossen; die Jobdatei
`setup/wrist_lighting/pending/left_rear.json` steht auf `COMPLETE`. Nicht erneut
in eine laufende Messreihe ausrollen oder Kameradienste dafür neu starten.

Am13.11. meldeten alle vier Kameras im alten Leerlaufzustand Schalter1
trotz Intensität0. Der explizite Aus-Befehl (Setter1) ergab bei allen vier
Schalter0 und Intensität0 bei wiederholter direkter Abfrage. Die älteren
Nachweise unter `setup/wrist_lighting/idle_check_20261113/` erfassten nur
Intensität0 als Aus-Kriterium. Die Nutzungsintensitäten bleiben erhalten.

```bash
systemctl --user status uwa-wrist-led-policy.service
journalctl --user -u uwa-wrist-led-policy.service -n 30 --no-pager
cat setup/wrist_lighting/pending/left_rear.json
```

Weiteres bewusstes Enrollment nur im Leerlauf:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
python3 -m uwa_cell_control.wrist_activity --enroll 192.168.8.103
```

## Nachweise

Rohbilder/Reports/Sensorwerte einschließlich verworfener Diagnoseversuche:
`setup/calibration/wrist_speed_led_20261112/`.
`led_quality_comparison.json`, `baseline_led_verified_right_front.json`,
`fast_led_comparison_2_right_front.json`, `cb3_{baseline,fast}_led_left_front.json`,
`rr_fast_led_right_rear.json`.

`live_led_leases.json`: zwei echte Vorschauprozesse; erster Absturz lässt Licht
für zweiten an, letzter Absturz führt zu bestätigtem Licht0, alle übrigen
Settings identisch. Bau/gezielte Regressionen:
`setup/logs/uwa-wrist-speed-led-{build,tests}.log`: Bau und45gezielte Tests bestanden.
Echte ROS-Aufrufe LF13,57s/RR24,39s mit bestätigtem LED0; Qt-Vorschau/LED-Knopf/
Schließen ebenfalls bestanden (`gui-led-preview.json`, `gui-led-active.png`).
Das Wrist-Fenster akzeptiert `--arm right_front|right_rear|left_front|left_rear`.
Prüfungen umfassen Mehrnutzer,
Absturz, fehlgeschlagenes Einschalten, aufgeschobenen Rollout, Modusrückfall,
Firmware-Shim und bestehende HD-/HTTP-/Kalibrier-/Capture-App-Pfade.
