# Studentischer Roboter: Aufnahme- und Pipeline-Test

Stand13.11.2026. Nutzer beauftragt die neue Pipeline am deutlich komplexeren
Roboternachbau zu testen. Grobe Maße laut Nutzer330×300×330mm. Ausgeschaltet,
unbeweglich einschließlich loser Teile; Unterseite auf Tischplattenhöhe bestätigt.
Für das Meeting hat der Nutzer anschließend die URs ausgeschaltet und ausdrücklich
Offlinearbeit bis zur erneuten Verfügbarkeit angeordnet.

## Erreichter Stand

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
