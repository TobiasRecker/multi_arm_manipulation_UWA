# Vierarm-Objektscan: realer Runner und aktueller Startstand

Stand:13.11.2026. Nutzer beauftragt ausdrücklich eine echte parallele Ausführung
und bleibt für den Versuch am physischen Nothalt. **Bisher keine reale Scanbewegung,
Power-/Brake-Aktion oder Safety-Quittierung ausgeführt.** Programme zur
Treiberwiederverbindung wurden am13.11. neu verbunden.

## Aktueller Blocker

**Update13.11.:** Alle vier Dashboards wieder RUNNING/NORMAL erreichbar.
Nutzer bestätigt Remote-Control vorne rechts, aktuellen Nothalt-Bediener sowie
unveränderten Aufbau und freie Fahrbereiche/Kabel. Die vier RTDE-Reader liefen
nach Netzausfall nicht wieder an; gespeicherte ROS-Werte widersprechen den
Dashboards. Gezielte Treiberwiederherstellung und neue Planung nötig. Noch
keine reale Fahrt gestartet. Neue Wege/Trennung und Hardware-Check bestanden;
Kamera-Fokusvorlauf vor Fahrt abgebrochen und anschließend korrigiert.
Stationärer Test aller fünf nativen Fotopfade läuft.

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
