# Studentischer Roboter: Aufnahme- und Pipeline-Test

Stand16.11.2026. Nutzer beauftragt die neue Pipeline am deutlich komplexeren
Roboternachbau zu testen. Grobe Maße laut Nutzer330×300×330mm. Ausgeschaltet,
unbeweglich einschließlich loser Teile; Unterseite auf Tischplattenhöhe bestätigt.
Für das Meeting hat der Nutzer anschließend die URs ausgeschaltet und ausdrücklich
Offlinearbeit bis zur erneuten Verfügbarkeit angeordnet.

Neue Offlineergebnisse16.11.: Ein [erster fototexturierter 3D-Formkandidat](student_robot_visual_hull.md)
ist exportiert; grobe Außenhülle, Gitter/Innenräume noch nicht rekonstruiert.
Die [konkrete LF-Kameradiagnose](left_front_camera_diagnosis_2026-11-16.md)
enthält Quellen, Zahlen und einen getrennt bearbeitbaren Diagnoseauftrag.

## Wiederaufnahme am16.11.

Der Nutzer hat Geräteverfügbarkeit und unveränderten, ausgeschalteten Aufbau
bestätigt. Der offene Kamera-Restore ist jetzt verifiziert; die fehlgeschlagenen
Originalversuche vom13.11. behalten ihre Fehlerflags.

Ein neuer stationärer Satz ist vollständig und brauchbar: vier native
2592×1944-Wristbilder plus OAK8000×6000. `all_usable:true`,
`stationary_set_confirmed:true`, `all_full:false` (Boards teilweise sichtbar,
ausreichend erkannte Ecken). Fokuskonfiguration danach wiederhergestellt.
Akzeptierter Satz unter `job/captures/20261116_103720_9f6d61d9/`,
Kontaktbogen `resume_20261116/five_camera_views.jpg`. Optik/Boardposen vorbereitet;
weiterhin erst **eine Ansicht pro Kamera**, kein vollständiger Mehransichtsscan.

Nach ausdrücklicher Nutzerfreigabe wurden ausschließlich die vier lokalen
ROS-Treiber geordnet mit `FASTDDS_BUILTIN_TRANSPORTS=UDPv4` neu gestartet und
das identifizierte `ros.urp` per Stop/Play wieder verbunden. Keine Power-/Brake-
oder Fahrbefehle. Dienst: `uwa-ur-drivers-udp-20261116.service`.
Alle vier RUNNING/NORMAL/Reverse verbunden; je fünf Zustandscontroller aktiv,
vier Bewegungscontroller inaktiv. Achtsekundenmessung mit frischen JointStates
aller Arme, Geschwindigkeiten maximal0,000137rad/s.
Nachweise: `resume_20261116/udp_restart_verification.json`,
`ur_after_udp_restart.json`, `program_restart.json`.

Zwei getrennte Treiberbefunde: Laufzeit-Spawner ohne Armnamespace übernahm keine
namensraumgebundenen Parameter; enger MATCH-Fix mit16 bestandenen Tests.
Außerdem waren Managementdienste zuvor zeitweise nicht erreichbar; der neue
UDP-Lauf funktioniert, die genaue Ursache ist noch nicht bewiesen.
ROS-Clients für diesen Lauf ebenfalls mit obiger UDP-Variable starten.

Neue gemessene Starts: `resume_20261116/snapshot_after_udp_restart.json`.
Darauf neu geplante zwölf Sicht-/Kollisionswege unter
`resume_20261116/view_plan/` sind modellgeprüft, weiterhin `executable:false`.
Die gebundene Abstandsprüfung in `resume_20261116/separation/` ist ebenfalls
bestanden: initial/extra/all für alle vier Arme unabhängig parallel nachgewiesen,
50mm Anforderung, 5mrad Trackingkorridor, kleinste untere Abstandsschranke349,7mm.
Geplante gemeinsame Fahrzeit59,1s ohne Fotos/Stillstand. Vollständiger Live-
Preflight unter `resume_20261116/preflight/`: CHECKED, drei Runden,
`motion_sent:false`. Das belegt diese konkreten Wege im Modell, keine allgemeine
Arbeitsraumtrennung oder Vermessung der vorläufigen Basis-/Tischanker.
Die aktuelle Bedienerbereitschaft am Nothalt und freie Fahrbereiche einschließlich
Kabel wurden anschließend ausdrücklich bestätigt; alle drei gemeinsamen Fahrten
sind ausgeführt. Es gab keine automatische Rückfahrt.

### Aufnahmeergebnis und Unterbrechung

Runde1/2 lieferten vollständige, stationär bestätigte Fünfersätze. Während der
letzten Fotoaufnahme wurden GUI und Runner unerwartet mit Exit143 beendet;
Ursache bislang offen. Zuletzt waren alle Arme bestätigt still und sämtliche
Bewegungscontroller deaktiviert. Der unabhängige Kameraworker beendete seine
Transaktion und bestätigte die Wiederherstellung aller vier Fokuskonfigurationen.

Der dritte Originalsatz ist vollständig, aber **nicht stationär bestätigt**:
vorne links maximal0,020229rad/s gemeldet bei0,276mrad Positionsspanne.
Keine Ursache aus diesen Werten behaupten, keine Grenzwerte verändern.
Originalmanifest und Laufstatus bleiben unverändert; dieser Satz wurde nicht
importiert. Nachprüfung aller vier Arme: Bewegungscontroller inaktiv, gemessene
Geschwindigkeitennull. Nur die Fotos wurden an der bereits erreichten Position
mit dem Kamera-only-Adapter und RTDE-Monitor wiederholt, ohne Fahrziel.

Wiederholung erfolgreich: `job/captures/20261116_113557_d094b3cc/`.
Runde1/2 liegen unter
`resume_20261116/scan_run/photos/20261116_113023_79c2ef06/`.
Zusammen mit dem ersten stationären Referenzsatz **vier akzeptierte Sätze,
20nativeBilder, vier unterschiedliche Standpunkte je Wrist und ein fester
OAK-Standpunkt**. Wiederholte OAK-Fotos zählen nicht als neue Standpunkte.
Kontaktbogen: `resume_20261116/accepted_views.jpg`.

Vorbereitung in10,307s abgeschlossen,20Ansichten, keine Importausschlüsse.
LF bleibt wegen vorhandener Kalibrierqualität von der metrischen Auswertung
ausgeschlossen; RF behält seine ursprünglichen nicht bestandenen Qualitätsflags.
Kein fertiges Mesh/Genauigkeitsnachweis. Nächste Stufe: geprüfte Objektmasken und
validiertes Mehransichts-Mesh-Verfahren; Anforderung in
`job/prepared/reconstruction_request.json`.

Alle Fokus-Restores und LED0 an allen vier Kameras bestätigt; Nachweise
`resume_20261116/final_camera_readback.json`, `post_interruption_verification.json`
und `scan_recovery_summary.json`. Das Aufnahmeziel wurde durch getrennte
Wiederherstellung erfüllt; der ursprüngliche Scanprozess ist ausdrücklich
**nicht COMPLETE**. Vor einem weiteren Hardwarelauf persistente Prozessführung
und Abbruchpfad prüfen. Keine weitere Fahrt für diese Wiederaufnahme nötig.

## Historischer Stand13.11.

- Frisches natives OAK-Bild gespeichert, offene Streben-/Rad-/Aufbaugeometrie
  sichtbar. Keine passende einfache Schalen-/L-Form; Familie `multiview_mesh`.
- Erster Fünfkamera-Versuch vor Bildern an Telemetrieaufbau gescheitert.
  Zweiter Versuch enthält drei Wrist-HD-Bilder plus OAK; LF-SSH nicht erreichbar,
  Stillstandssatz und Fokus-Restore am Ende nicht bestätigt. Die Hardware wurde
  laut Nutzer ausgeschaltet. **Kein gültiger vollständiger Scan**, keine Pose-
  oder Meshfreigabe daraus. Originale und Fehlerflags bleiben unverändert.
- Es gab keine Armfahrt, keinen Driver-/Power-/Brake-/Play-Befehl aus dieser Arbeit.
- Neuer Auftrag mit ID `student_robot_v1`, gewünschte drei Standpunkte je Wrist.
  Geometrie/Tracking NOT_TESTED, Manipulation NOT_APPROVED, Kamera-Restore offen.

Lokaler Ordner: `setup/digitization/student_robot_20261113/`.
Auftrag: `job/`; Übersichtsbild: `overview.jpg`; unvollständige Ansichten:
`partial_views.jpg`; vollständige Originale/Fehler in `job/captures/`.
Keine Originalfotos im Repository.

## Offline vorbereitete Ansichten

Der Nutzerauftrag erlaubt die Vorbereitung mehrerer Wristansichten. Aus dem
OAK-Bild und bestätigter Auflagehöhe ist eine **Planungshülle** abgeleitet:
ca546×546×403mm. Das größere horizontale Quadrat berücksichtigt unbekannte
Objektdrehung und einen angenommenen50mm-Zentrumszuschlag. Die Höhe enthält
ebenfalls einen Entwurfszuschlag. Das ist kein CAD, keine gemessene Unsicherheit
und keine Garantie vollständiger physischer Erfassung.

Die erste Suche bei geringeren Abständen fand keinen gemeinsamen Fünfkamera-
Blick. Eine zweite, größere Abstandssuche behielt dieselbe Hülle sowie dieselben
Kollisions-/Sichtgrenzen und fand **zwölf geprüfte Bewegungsabschnitte**:
eine Grundansicht und zwei zusätzliche Blickwinkel pro Wrist, plus feste OAK.
Zusatzkandidaten können echte±12°-Orbits nutzen; sie gehen weiterhin durch IK,
Sicht-/Kollisions- und vollständige Verbindungswegprüfung. Ein großer Winkel ist
kein pauschaler Bewegungsfreiraum.

Ergebnisse: `offline_view_plan_wide/report.json`, `cell.urdf`, einzelne
`review_step_*.json` und `preview.png`. Ausgangsmodell: `job/planning/envelope.json`
und `envelope_review.jpg`; erste erfolglose Suche unter `offline_view_plan/`.
Geprüfte Wege haben0,05rad/s und0,10rad/s² als Planungsgrenzen.

Die Startwerte wurden aus **älteren, rein lesenden RTDE-Messungen vor dem
Abschalten** zusammengesetzt, nicht aus aktuellen oder synchronen Gelenkständen.
Snapshot heißt ausdrücklich `historical_planning_snapshot.json`,
`snapshot_is_current:false`, `execution_authority:false`. Alle Berechnungen
danach waren offline/Domain74; keine weitere UR-Abfrage.

**Noch keine reale Ausführungsfreigabe:** Die modellgeprüften Verbindungen
sind zunächst sequenziell geprüft. Unabhängige gleichzeitige Ausführung ist
damit nicht nachgewiesen. Welt-/Tischanker bleiben vorläufig; Kabel/Personen
sind keine automatisch erfassten Modellhindernisse.

## Fortsetzen nach dem Meeting

Der Nutzer braucht zunächst nur die URs wieder einzuschalten und Bescheid zu
geben. Vor Fotos/Fahrten folgen dann konkret:

1. Echte Geräte-/Kameraerreichbarkeit und neue gemessene Zustände lesen.
   Native LF-HD-SSH-Verbindung erneut prüfen; nichts aus früheren Starts annehmen.
2. Ursprüngliche Kameraeinstellungen der fehlgeschlagenen Sitzung über den
   ausdrücklichen `recover`-Adapter wiederherstellen und verifizieren.
3. Ansichtspfade mit frischem Start und unverändertem Aufbau neu binden und
   prüfen. Die historische Datei nicht in einen aktuellen Nachweis umbenennen.
4. Nötige Treiber-/Programmbedienung getrennt durchführen und aktuelle Bediener-
   bereitschaft am Nothalt klären, bevor echte Ziele gesendet werden. Kein
   automatischer Play-/Fahrstart allein durch Öffnen oder Jobfortsetzung.
5. Neue vollständige native Fotosätze an den geprüften Standpunkten aufnehmen.
   Erst bestätigte Sätze importieren; wiederholte statische OAK-Fotos zählen
   nicht als zusätzliche OAK-Standpunkte.

Die neue Routine ist in [digitization_workflow.md](digitization_workflow.md)
beschrieben. Der komplexe Roboter benötigt danach zusätzlich Objektmasken und
einen validierten Mehransichts-Mesh-Backend. Dieser ist noch nicht angebunden;
das Paketieren eines parametrischen Entwurfs löst diese Stufe nicht automatisch.
