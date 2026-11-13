# Vierarm-Objektscan: realer Runner und aktueller Startstand

Stand: 13.11.2026. **Alle fünf Stellungen je Roboter und 25/25 Bilder sind
abgeschlossen.** Alle Arme stehen; Fahrcontroller sind inaktiv. Keine automatische
Rückfahrt oder neue Fahrt beim Öffnen des Statusfensters.

Die anschließende Offlineauswertung liefert einen ersten
[Karton-CAD-Entwurf mit Ausschnitten und Fototexturen](carton_multiview_2026-11-13.md).
Die dort dokumentierten Mehransichtsfehler bleiben offen; kein metrischer PASS.

## Ergebnis

- Index: `setup/digitization/four_arm_scan_20261113/scan_dataset.json`.
  20 native Wrist-Ansichten2592×1944 und fünf OAK-Fotos8000×6000, zusammen
  21verschiedene Kamerastandpunkte. Bildhashes, native Größe, fester Fokus,
  Sollpose und tatsächlicher Stillstand je Gruppe geprüft. Mindestens12ChArUco-
  Ecken je Wrist-Bild und24je OAK-Foto. Keine metrische Rekonstruktionsfreigabe.
- Vorschaubilder: scan_overview.jpg und scan_all_rounds.jpg im selben Ordner.
  Originale und fehlgeschlagene Versuche unverändert erhalten. Der vorherige
  scan_dataset_partial.json bleibt als historischer Zwischenstand erhalten.
- Initiale gültige Gruppe nach Nutzer-OAK-Neustart; Runden2–4 aus run03_rest,
  letzte Gruppe aus last_round_post_os147. Die vier Arme waren für die späteren
  Foto-Wiederholungen bereits an ihren Endstellungen; keine zusätzliche Fahrt.

## OAK-Update und Nachprüfung

Das vom Nutzer ausdrücklich freigegebene Hersteller-OTA1.32.1→1.47.0 wurde
installiert, Agent0.28.0 und dieselbe Geräte-ID bestätigt. Werkskalibrierung
vor/nach OTA exakt identisch; SDK3.12 und globale Kalibrierprofile unverändert.
15direkt aufeinanderfolgende nativeStart-/Fotozyklen bestanden, anschließend
der komplette letzte Fünfkamera-Satz mit unabhängigem Stillstandsaudit.
16erfolgreiche OAK-Aufnahmen nach Update sind ein begrenzter Wiederholungsnachweis.

Der Datenindex weist OS1.32.1 für OAK-Gruppen1–4 und1.47.0 für Gruppe5 aus.
24gemeinsame statischeBoardecken vor/nach OTA verschoben sich um0,52nativePixelRMS;
das enthält Detektions-/Beleuchtungseinflüsse und ist keine neue Kalibrierung.
Update-/Paket-/Factory-/Testnachweise: setup/oak4/stability_20261113/ota/.

## Überwachung und Endzustand

Beim ursprünglichen letzten Fotoversuch lösten Telemetrielücken den Stopp aus;
PC-Treiber protokollierte2,18s Zykluszeit. Nachgewiesene Endstellungen blieben
erhalten. Fehlgeschlagene Bildsätze wurden nicht nachträglich als PASS markiert.
Kameraarbeit und read-only Audit laufen nun in eigenen Prozessen, unabhängig
vom Bewegungswächter. Ursprüngliche Frische-/Driftgrenzen gelten weiter.
OpenCV-Threads sind begrenzt; das temporäre Planungsobjekt bleibt vor Bildarbeit
nicht gehalten. 87gezielte Softwaretests bestanden; Hostressourcen und die
frühere Zyklusverzögerung bleiben für spätere automatische Fahrten relevant.

Letzte Prüfung: alle vier RUNNING/NORMAL, tatsächlicher Stillstand, Fahrcontroller
inaktiv. Linke Programme STOPPED, rechte PLAYING. OTA und Nachprüfung starteten
keinen Roboter, lösten keine Bremse und sendeten keine Arm-/Programmaktion.

Historischer Ausfall am12.11.:

Während der Vorbereitung fiel die Verbindung zum Roboternetz aus:
`enp87s0` ist DOWN/unavailable, Carrier OFF, keine192.168.8.209-Adresse mehr.
Alle vier UR-Dashboards antworten nicht. Die ROS-Broadcaster liefern weiterhin
scheinbar frische JointStates aus gespeicherten Hardwarewerten. Das ist **kein
Nachweis aktueller Roboterkommunikation**. Zuletzt gemeldete RobotMode-Werte3
(POWER_OFF), beide Rear-Safety-Werte9(FAULT) sind ohne erreichbares Dashboard
keine verifizierte aktuelle Gerätezustandsabfrage. Nicht automatisch quittieren.

Nutzer wurde um Prüfung von Kabel/Switch/Steuerungen gebeten. Kein automatischer
Start bei Linkwiederkehr; dieser Runner ist noch nicht an echter Hardware gestartet.
Vor Fortsetzung Verbindung und native Zustände prüfen und einen neuen eindeutigen
JointState-Snapshot/Plan anlegen. Alte Sitzungsdaten nicht überschreiben.

## Neu vorbereitete Geometrie

Der erste Entwurf ließ die hinteren Zusatzwege nicht unabhängig parallel zu.
Für den neuen Auftrag Zielposen mit60mm Abstand zu den eigenen Paar-Trennebenen
gefiltert; anschließend sämtliche Verbindungswege und Bewegungsräume neu geprüft.
Reserveansichten ersetzen einen ausgeschlossenen rechten Frontblick.

- Vier zusätzliche Stellungen je Arm, zusammen mit Grundansichten/OAK21verschiedene
  Blickpunkte. Fünf Aufnahmerunden mit je fünf Fotos sind vorgesehen.
- Neuer Modellnachweis: alle vier Arme in initial/extra/all unabhängig vom
  Zeitversatz getrennt, geforderter Restabstand50mm **nach** Zwischenpunktpolstern
  und±0,005rad überwachten Gelenkbahnabweichungen. Kleinste berechnete
  Abstandsuntergrenze339,0mm. Keine gemessene absolute Montagegenauigkeit daraus.
-2400Wegpunkte gegen vollständige MoveIt-Szene einschließlich Objekt geprüft.
  Quellplan, Modell und Mesh-Hashes gebunden. Greiferwerte bleiben explizite
  Modellannahmen; keine echten Greiferstellungen neu gemessen.

Dateien unter `setup/digitization/four_arm_scan_20261112/`:
`plan_wall60_reserves/`, `separation50_tracking005/`, `static_model_recheck.json`.
Diese erste Vorbereitung ist **historisch**: erneute Statuslesung ersetzte die
ursprüngliche Latest-Snapshot-Datei. Die kopierten Startwerte bleiben im Plan,
aber dessen Snapshotbindung ist dadurch nicht mehr gültig. Der Runner weist
fehlende/geänderte Originalsnapshots ab; vor Ausführung frisch neu planen.
Nachfolgende Statuslesungen haben eindeutige Zeitnamen. Originalbilder wurden
nicht verändert/überschrieben; aus diesem Auftrag gibt es noch keine echten Fotos.

## Ausführung und Stopp

Neue Module `parallel_scan.py` und `parallel_scan_gui.py`, Einstieg:

```bash
# Eigenständiges englisches Stop-/Statusfenster, Hardware-Domain66:
bash src/multi_arm_manipulation_UWA/scripts/object_scan.sh gui

# Nur frische Zustands-/Modell-/Pfadprüfung; kein Bewegungsziel:
bash src/multi_arm_manipulation_UWA/scripts/object_scan.sh check \
  --plan /absolut/zum/NEUEN/report.json \
  --analysis /absolut/zum/NEUEN/separation.json \
  --output /absolut/zum/NEUEN_check_dir

# Explizite reale Ausführung, vorhandene native Programme müssen bereit sein:
bash src/multi_arm_manipulation_UWA/scripts/object_scan.sh run \
  --plan /absolut/zum/NEUEN/report.json \
  --analysis /absolut/zum/NEUEN/separation.json \
  --output /absolut/zum/NEUEN_run_dir
```

Ausgabeverzeichnisse müssen neu sein. Der Wrapper bereinigt störende Snap-GTK-
Variablen vor Qt. Er öffnet standardmäßig ausschließlich das Stopfenster.
Die GUI allein sendet keine Fahrziele und startet keine Treiber/Programme.

Der Runner:

- prüft exakte Plan-/Snapshot-/Inventar-/URDF-/Meshbindung, Sourcequintiken,
  gleich viele Zusatzansichten je Arm und0,05rad/s/0,10rad/s²;
- verlangt alle vier Phasenräume mit50mm Abstand und dem überwachten0,005rad-
  Bahnkorridor, prüft das aktuelle Kollisionsmodell und alle ursprünglichen Wege;
- liest alle vier Arme frisch, kontrolliert zudem unabhängig über bestehende
  reine Dashboard-Abfragen echte Geräteerreichbarkeit, RUNNING, Safety und PLAYING;
  scheinbar frische gecachte ROS-Joints reichen nicht;
- sendet vier native FollowJointTrajectory-Ziele asynchron. Zeitgleichheit ist
  für die geprüfte Trennung nicht erforderlich. Ein Fehler/Abbruch eines Arms
  stoppt den gesamten eigenen Ablauf;
- prüft Safety, Programm-/Hardwareverbindung, Gelenkbahn, Fremdbewegung,
  Telemetrie und GUI-Heartbeat auch während Bildaufnahme. Kameraarbeit läuft
  in einem separaten Thread, Status-/Stop-ROS-Schleife bleibt aktiv;
- cancelt bekannte Ziele sofort, deaktiviert eigene beanspruchte Fahrcontroller,
  behandelt auch späte Zielbestätigungen und bestätigt Stillstand aus Messwerten.
  Bei fehlender Bestätigung folgt zusätzlich der native Dashboard-Stop;
- sperrt Fortsetzen nach STOP. GUI-Verlust, Schließen oder Ctrl+C führen ebenfalls
  zum Abbruch. Die rote Taste zeigt Annahme und bestätigten Stillstand getrennt;
- deaktiviert nach jeder Runde die Fahrcontroller, bestätigt Stillstand und nimmt
  fünf native Bilder auf. Nach der ersten Runde wird zur Bildprüfung angehalten;
  Continue ist nur in diesem Pausenzustand wirksam. Kein automatisches Rückfahren.

Power/Brake/Play sind bewusst nicht Bestandteil dieses Runners. Falls für den
konkret beauftragten Versuch erforderlich, ausschließlich den bestehenden
expliziten MATCH-Startablauf verwenden; keine Sicherheitszustände automatisch lösen.
Reale Montageabweichungen, Kabel/Personen und unmodelliertes Stativ bleiben
Grenzen des geometrischen Modells. Software-Stopp ersetzt nicht den physischen.

## Bereits geprüft

- Build und34gezielte Tests PASS (Bahn-/Safety-/Heartbeat-/Quellbindung,
  Stoppreihenfolge, Planung, Separation und Fünfkamera-Transaktionen).
- Vier echte native ROS-Trajektoriencontroller mit Fake-Hardware auf isolierter
  **Domain75**, ohne reale Roboternetzverbindung: alle vier Ziele erreicht.
- Gemeinsamer Trigger-STOP während Bewegung: alle vier Ziele gecancelt,
  Fahrcontroller inaktiv, tatsächlicher Mock-Stillstand bestätigt.
- GUI-Heartbeat während Bewegung verloren: alle vier gestoppt, Resume danach
  abgewiesen. Mock-Launcher anhand PID/Startzeit verifiziert gezielt beendet;
  alle eigenen Mock-Prozesse sauber beendet, reale Dienste erhalten.
- Separates Stopfenster geöffnet/gerendert, natives RobotMode-Monitoring zunächst
  ausschließlich lesend geprüft. Snap-Library-Startfehler korrigiert.
- Weiterhin offen: neue Live-Vorbereitung nach Netzrückkehr und der tatsächliche
  Hardwarelauf einschließlich erster Bildkontrolle. Keine Durchführung behaupten.
