# Vier URs in Beobachtungsstellung und sechs Kameras

Stand23.11.2026, Abschluss14:40AWST. Nutzer beauftragte die seriellen
Beobachtungsfahrten nach dem N100-Betriebswechsel und anschließend die
Sechskamera-GUI. Alle vier geometrisch berechneten Ziele wurden erreicht;
alle sechs aktuellen Vorschaubilder sind im sichtbaren Fenster bestätigt.

## Ergebnis

| Arm | Letzte erfolgreiche Fahrt [s] | Max. gemeldete Gelenkgeschwindigkeit [rad/s] | Max. Gelenkzielfehler [rad] |
|---|---:|---:|---:|
| left_front | 32.66 | 0.100380 | 0.0001326 |
| left_rear | 55.32 | 0.093394 | 0.0000586 |
| right_front | 51.48 | 0.093383 | 0.0000311 |
| right_rear | 59.19 | 0.094257 | 0.0000442 |

LF hatte vorher bereits einen Teil des Wegs zurückgelegt. Erfolgreiche Folge:
LF → LR → RF → RR. Größter Endfehler0,0001326rad; letzter GuardbefundCLEAR,
keine aktuellen Fehler. Alle Ziele einschließlich RF-Basis+51,9° im
entdrillten Umlauf erhalten. Keine Greiferaktion und keine neue Kalibrierung.

Nutzer erteilte nach dem ersten Geschwindigkeitsstopp ausdrücklich eine
**auf diese vier Anfahrten beschränkte Sollgrenze0,09rad/s**. Aktives Profil,
nominelle Überwachungsgrenze0,1rad/s und vorhandener Toleranzfaktor1,05
blieben unverändert. LF-Spitze0,10038 liegt unter der vorhandenen0,105-
Auslöseschwelle. Keine dauerhafte Tempoänderung für andere Programme.

## Betriebsereignisse und konkrete Korrekturen

1. Beim Wiedereinstieg lief bereits ein separater`ur_cell_power.py start`
   aufN100. Das eigene Startwerkzeug wurde durch dessen Lock abgewiesen.
   Im zugehörigen Startfenster meldete der Guard LR/wrist2−0,19530,
   RF/elbow+0,15838 und RR/wrist3+0,26192rad/s bei nominell0,1rad/s.
   Der vorhandene Schutz stoppte die Programme. Nur der positiv identifizierte
   StartprozessPID1386937 wurde mitSIGINT unterbrochen, Schutzprozesse erhalten.
   Die alten Holdziele nach ausgeschalteten Nullwerten sind eine plausible
   Ursache; interne Sollwerte wurden nicht direkt ausgelesen. Deshalb wurden
   die vorhandenen unbeladenen Holds beiSTOPPED an aktuelle übereinstimmende
   Driver-/RTDE-Winkel neu gebunden. Kein Positionsversand dabei.
2. Erster geprüfter LF-Anlauf mit Soll0,1rad/s stoppte um14:15:01 bei
   gemeldeten0,108457rad/s an wrist3. Ursprünglicher Plan55,42s,
   tatsächlicher Ablauf einschließlich redundanter N100-Prüfung173,80s.
   Keine Fortsetzung oder Absenkung vor der ausdrücklichen Nutzerfreigabe.
3. Restwege aufROSmini erneut vollständig geprüft. Gleichmäßige Zeitskalierung
   auf0,09rad/s erhält die Geometrie und senkt Beschleunigungen quadratisch.
   SHA-gebundene Dateien, aktive Hardware-/Mesh-/Configbindung und identische
   Prüferquellen werden aufN100 geprüft. Existierende frische Start-,
   Stillstands-, Korridor-, Action- und Vollzellprüfungen bleiben aktiv.
   Die vollständige Offline-Zeitparametrisierung wird dort nicht wiederholt.
4. LF/LR erreichten die Ziele. RF war noch durch eine asynchron quittierte,
   nicht vollständig angewendete Freigabe blockiert. Ein gezielter Reset
   bestätigte danachRF frei, löste beim Wiederaufwecken alter Ressourcen-
   nachweise jedoch einen administrativen nativen Stopp aus. Um14:27:48
   meldeteRF`native hardware verification unavailable, age_s=257.802770`.
   Danach Watchdog/STOP_ADAPTER_LOST; alle Programme gestoppt.
5. Bei neuer Clienterzeugung um14:32:18 erneuter Watchdog-/Adapterverlust
   vor der rechten Fahrt. Dies passt zum bereits dokumentierten Problem mit
   wiederholtem Graphauf-/abbau. Die endgültige Ausführung baut **einen
   gemeinsamen Client samt Actions/Lesern vorPlay** bei gestoppten Programmen
   auf, wartet jede tatsächlich angewendete Freigabe ab und behält ihn über
   beide verbleibenden Armabschnitte. RF/RR danach erfolgreich, keine weiteren
   Grenz-/Schutzparameteränderungen oder Schutzdienstneustarts.

Nicht als allgemeine Fehlerfreiheit der N100-Runtime ausgeben. Verwaltungs-
frische beim Cache-Aufwecken und Verbindungsaufbau bleiben diagnostische
Befunde für deren weitere Pflege. Der vorliegende Auftrag wurde über den
bestehenden, korrekt vorbereiteten und überwachten Pfad abgeschlossen.

## GUI und Daten

`UWA Camera Capture` sichtbar geöffnet, alle sechs Livebilder am23.11.
ab14:40:10AWST bestätigt. Vier HTTP-Handkameras640×480 in der Vorschau,
Ethernet-OAK4 SDK2000×1500, USB-OAK N1001280×960. Native Aufnahme:
Handkameras2592×1944, OAK48000×6000, USB4056×3040. USB-Anzeige180°,
Rohbilder/Messkoordinaten ungedreht. **CAPTURE ALL SIX**; Board die gesamte
Serie bisDONE stillhalten. Unterschiedliche Blickpaare zwischen Serien.

Aktuelle Sitzung: `/home/rosmatch/UWA_ws/setup/calibration/six_camera_mobile/20261123_143953_b34a17a2`.
Fensterdienst aufROSmini:`uwa-camera-capture-six-20261123.service`.
Pause/Schließen gibt die eigenen Kameraleases frei. Beim Start wurde ein
Shell-`nounset`-Fehler des operativen Launchers korrigiert; ROS-Umgebung
wie beim vorhandenen Launcher mit`set -eo pipefail` laden.

Quellen/Nachweise im Workspace:

- `setup/calibration/mobile_volume_20261123/execution-01/final-verification.json`
- `execution-01/frozen-02/`: erfolgreiche LF/LR-Befunde und spätere RF-Sperre
- `execution-01/persistent-05/`: erfolgreicheRF/RR und reguläre Programmstarts
- `execution-01/plans-02/`, `plans-03-remaining/`: exakte geprüfte Restwege
- `execution-01/startup-incident/`: Anfangsvorfall mit Messwerten/Journal
- `gui-live-status.json`, `six-camera-live.png`: eigenes Fenster, reale sechsFeeds
- `config/digitization/six_camera_capture.yaml`: nur Aufnahmeparameter
- `tools/prepare_calibration_observation_motion.py` und
  `tools/execute_calibration_observation_motion.py`: Offline-Compiler / Dispatcher

Die28 gezielten Kamerasoftwaretests und der Lyrical-Paketbuild bestanden.
Dateibindung und Sollgrenze des neuen Dispatchers wurden vor der echten
Ausführung geprüft; veränderte SHA bzw. nicht genehmigte Sollgrenze abgewiesen.
