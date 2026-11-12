# Native HD-Bilder der beiden hinteren Wrist-Kameras

Stand12.11.2026. Nutzerauftrag: denselben nativen HD-Zugriff wie rechts vorne
auf rechts hinten und links hinten testen. Ausschließlich Kamera-/SSH-/ROS-
Bildzugriff, **keine Roboterbewegung oder Dashboard-/Brems-/Programmbefehle**.

| Arm | IP | Installierte Kamera-Software | Native Bilder | Vollständiger ROS-Diensttest |
|---|---|---|---|---|
| left_rear |192.168.8.169 |UCC3.44.0.149696 / CQ0-1.4.0 |3×2592×1944, je24 ChArUco-Ecken | **PASS**, Originalsettings/Normal bestätigt |
| right_rear |192.168.8.170 |UCC1.11.1.10337 / CQ0-1.3.5 |3×2592×1944, kein Board im Blick | **FAIL im Autofokusmodus**, Fokusfenster-Restore nicht identisch |

Damit ist der native Bildpfad an beiden Kameras nachgewiesen. Ein Firmwareupdate
war für die eigentliche Aufnahme nicht nötig. Der rechte Rear-Dienst ist im
getesteten Autofokusmodus noch nicht für unbeaufsichtigte Serien geeignet.
Es wurden keine neuen Intrinsics/Hand-Auge-Parameter für diese Kameras geschätzt
und keine Front-Kalibrierung auf andere physische Kameras übertragen.

## Links hinten: erfolgreicher Dienstaufruf

Drei nativeJPEGs,2592×1944; Kamera-ID`06561F1400090106`. Je24 linkeBoard-Ecken,
keine Skalierung/Farbkorrektur. Gesamter Aufruf16,12s, `restore_ok:true`,
`all_original_fields_match:true`, tatsächlicher Kamera-ZustandNormal.
Fokus406Manual,33333µsManual/Gain16 und übrige Werte identisch.

Daten:
`$UWA_WS/setup/calibration/wrist_hd/service/left_rear/c1990d41963846b78e3346ee5b3a8b5d/`

Bild: `frame_002.jpg`, vollständiger Nachweis in `validated.json`.
Der Service bleibt aufDomain66 erreichbar:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 service call /uwa_hardware/left_rear/wrist_camera_hd/capture std_srvs/srv/Trigger '{}'
```

Die temporäre privateSSH-Sitzung muss noch gültig sein; andernfalls interaktiv
`ros2 run uwa_cell_control wrist_hd_service --arm left_rear --connect`.
Kein Kennwort wurde in Dateien gespeichert.

## Rechts hinten: Bild erhalten, Restore-Limit erkannt

Kamera-ID`01D1111A00090912`, nativeJPEGs in:
`$UWA_WS/setup/calibration/wrist_hd/service/right_rear/f3721293090c4b5f96b7a1c526238d5d/`

Beispiel `frame_002.jpg`: Kamera zeigt aus der bestehenden Parkstellung Richtung
Decke/Leuchte, kein ChArUco-Board sichtbar. Das Bild ist unscharf; dieser Test
vermisst keinen festen Fokus. Es wurde kein Arm für ein schöneres Motiv bewegt.

Der erste Neustart/Moduswechsel änderte das Autofokusfenster von
X1/Y1=165/134 auf158/118; ein zweiter Versuch änderteY1 weiter auf102.
X2/Y2=450/339 bleiben gleich. Die altenROI-Koordinaten ließen sich über denselben
HTTP-Setter nicht exakt wiederherstellen. Diese Abweichung wird ausdrücklich
nicht als erfolgreicher Restore akzeptiert. Autofokus/Autoexposure sind wie zu
Beginn eingeschaltet; deshalb dürfen ihre automatisch bestimmten Fokus-/
Belichtungswerte variieren. LED-Modus und sonstige Konfiguration sind erhalten,
Kamera-ZustandNormal. Bestehende Rear-VGA-Kalibrierung verlangt dagegen ihren
festen manuellen Fokus404; ein Autofokusbild ist kein Nachweis dieses Profils.

Weitere nativeAufrufe mit **UCC1.11.1+focusAuto=true** werden jetzt **vor jedem
Modus-/Dienstwechsel** abgewiesen. Real geprüft: früher Abbruch in2,88s,
`state_changed:false`, alle Vorher-/Nachher-Settings identisch.
Ein verifiziertes manuelles Fokusprofil oder ein URCap-Update mit erneuter
Restore-Prüfung ist für weitere Serien erforderlich. Beides wurde hier nicht
ungefragt als Firmware-/Fokusänderung durchgeführt.

## Unterschiede der älteren Versionen und Prüfungen

Bei den beiden tatsächlich getesteten alten ZweigenUCC1.11.1/3.44.0 ist die
LED-Schreibcodierung0/1 gegenüber dem Readback invertiert. Der Worker berücksichtigt
dies ausschließlich für diese Zweige und verlangt anschließend den gewünschten
tatsächlichen Readback. Das hat links den vollständigen Restore ermöglicht.
Außerdem werden verzögerte Einstellungen begrenzt abgewartet. Bei Autofokus bzw.
Autoexposure gelten die berechneten Ausgabewerte als dynamisch; die Modi und
sämtliche übrige Konfiguration einschließlich Fokusfenster bleiben streng geprüft.
Bei manuellem Fokus/Belichtung bleiben die Zahlenwerte exakt geprüft.

Quellcode-/Consumer-Prüfung zusammen mit Front-Übernahme:45 Tests bestanden,
drei Lyrical-Pakete gebaut. Lokale Test-/Restoredaten unter
`setup/calibration/wrist_hd/other_arms_20261112/`, insbesondere
`left_rear-final-result.json`, `right_rear-final-result.json`,
`right_rear-guard-result.json`, `images-summary.json` und endgültiger Readback.
Fehlgeschlagene Erstversuche/Originale sind erhalten. SSH ausschließlich auf
Kameraoperationen begrenzt; Hardwaretreiber/andere Dienste nicht neu gestartet.
