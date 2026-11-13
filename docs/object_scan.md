# Objektaufnahme: OAK zuerst, dann vier Wrist-Kameras

Stand: 13.11.2026. Die reale parallele Fahrt mit fünf Stellungen je Arm wurde
inzwischen ausgeführt. 20 Wrist-HD-Ansichten und fünf native OAK-Fotos sind
bestätigt; der Datensatz enthält25/25Bilder. [Ergebnis und aktueller Haltstand](parallel_object_scan.md).
Der folgende Nachweis vom12.11. beschreibt die frühere Offline-Vorbereitung.

## Ablauf

1. Ein einzelnes natives OAK-Farbfoto aufnehmen, Fokus passend zur Factory-K/D.
2. Boardpunkte automatisch erkennen; sichtbare äußere Objektecken ausdrücklich
   zuordnen und im Overlay prüfen. Dieser Schritt ist noch assistiert, keine
   automatische Segmentierung beliebiger Objekte.
3. Grobe Rechteckgeometrie aus dem Foto und der gemeinsamen Auflageebene fitten.
   Maßstab kommt vom Board; Nutzermaße dienen als Startwert und Planungsreserve.
4. Ein größeres Planungsvolumen erzeugen und gemeinsame Wrist-/OAK-Ansichten
   sowie vollständig kollisionsgeprüfte Verbindungswege suchen.
5. Nach Durchsicht und frischer Prüfung der konkreten Wege real positionieren.
   Der neue Planer enthält selbst **keine Bewegungs-Clients**.
6. Ruhende Szene mit vier nativen Wrist-Kameras und OAK aufnehmen. Aus zusätzlichen
   Ansichten später Geometrie/Mesh/CAD bestimmen und unabhängig prüfen.

Das grobe OAK-Modell dient der Planung. Seine Abmessungen sind keine abschließende
Vermessung. Einseitig verdeckte Details und unregelmäßige Kartonwände bleiben
Annahmen; bessere Maße folgen aus mehreren Ansichten und Kontrollmessungen.

## OAK-Foto und grobe Schätzung

Aus dem Workspace, nach Build von `uwa_cell_control`:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 run uwa_cell_control object_scan_bootstrap \
  --capture-oak --output "$UWA_WS/setup/digitization/NEUE_SITZUNG/overview"
```

Nutzt ausschließlich den vorhandenen OAK-Fotodienst: ein Standard-RGB-Frame,
8000×6000, Fokus116, kein Tiefenbild. Keine fremden Kameraprozesse stoppen.
Speichert Fotoverweis, SHA-gebundene Annotationvorlage und 1600px-Prüfbild.
Bereits gespeicherte `result.json` alternativ mit `--oak-result DATEI` verwenden.

Die Vorlage hat `ids: [4,5,6,7,2,3]`: vier obere Rechteckecken und die beiden
sichtbaren vorderen Auflageecken. Die Nummerierung entspricht `digitize_box`:
0–3 unten im Umlauf, 4–7 darüber, Board-Z zeigt in die Platte. `pixels` beziehen
sich auf das vollständige 1600px-Prüfbild, `proxy_width` muss dazu passen.
`user_rough_size_m` ist optional; Angaben und Annotationherkunft kennzeichnen.
Der Assistent kann diese Zuordnung übernehmen, das Overlay bleibt durchsehbar.

```bash
ros2 run uwa_cell_control object_scan_bootstrap \
  --oak-result /absolut/zur/overview/oak_result.json \
  --landmarks /absolut/zur/geprueften_annotation.json \
  --output /absolut/zur/overview/estimate
```

Ergebnis: `estimate.json`, `overview_estimate.jpg`, `scan_geometry.yaml`.
Bildgröße, tatsächlicher Fokus, Originalhash und unabhängige Board-PnP werden
geprüft. Degenerierte/grobe inkonsistente Fits werden abgewiesen. Keine neue
Kamerakalibrierung und keine Weltpose aus Bildfehlern als Ground Truth behandeln.

Planungsmaße aktuell je Achse:
`max(Bildschätzung, grobe Nutzerangabe) × 1,15 + 0,04 m`.
Das ist eine bewusste Entwurfsreserve, **keine bewiesene Unsicherheitsschranke**.
Welt-/Tischanker bleiben vorläufig; ein größeres Objektvolumen ersetzt diese
fehlende geometrische Vermessung nicht.

## Bewegungsfreie Planung und Durchsicht

```bash
ros2 run uwa_cell_control object_scan_plan \
  --read-live-state \
  --config /absolut/zur/estimate/scan_geometry.yaml \
  --output /absolut/zur/plan

# Bereits gemessener Zustand für reproduzierbare Offline-Prüfung:
# --snapshot DATEI statt --read-live-state

# Einzelnen Verbindungsweg ausschließlich in RViz ansehen, Domain74:
ros2 run uwa_cell_control object_scan_plan \
  --output /absolut/zur/plan --preview-step 0
```

Vier aktuelle JointState-Eingänge sind erforderlich; kein Ersatz durch Home oder
Simulationsnullen. Eine gespeicherte Messung bleibt eine Messung ihres Zeitpunkts.
Ein erfolgreicher Entwurf ist `executable:false`; bevor eine reale Fahrt entsteht,
Startzustand/Modell/Wege erneut prüfen und die konkrete Route durchsehen.

IK und Sichtprüfung betrachten die ganze Objektbox, andere Arme und sichtbare
Referenzmarker. Ein linkes **oder** rechtes Board darf die Bildreferenz liefern.
Kollisionsprüfung mit MoveIt gegen Tabellen, Boards, Arme, Greifer, Kameras,
Boden und zusätzliches gepolstertes Objektvolumen. Alle Verbindungen werden als
zeitparametrierte lokale Gelenkwege abgetastet; blockierte Verbindungen werden
abgelehnt, keine ungeprüften Ausweichwege. Grenzen:0,05rad/s und0,10rad/s².
Keine Diagonalausnahme für diese neue gemeinsame Objektaufnahme.

Zunächst serielle Grundpositionierung. Zusätzliche ±2cm-Vorschläge liegen in den
Kamera-X/Y-Richtungen, mit erneuter IK-, Sicht- und vollständiger Wegprüfung.
Ein lokales Gelenkfenster verhindert große IK-Sprünge. Endpunktprüfung allein
reicht nicht. Kabel, Personen und das bisher nur visuelle Stativ fehlen weiterhin
in der Kollisionsszene; ursprüngliche UR-Sicherheit bleibt erhalten.

`report.json`, `cell.urdf` und `review_step_NNN.json` sind getrennte Prüfartefakte.
Die RViz-Vorschau zeigt das grobe Objektvolumen orange, keine Hardware-Kommandos.
Statische Skizze optional mit `tools/preview_object_scan.py --report ... --output ...`.

## Parallele Prüfung der Bewegungsräume

Der neue [Trennwand-/Hüllenbericht](scan_separation.md) betrachtet die vollständigen
Wege unabhängig vom Zeitversatz. Aktueller Modellbefund: Anfangswege aller vier
Arme getrennt; bei Zusatzansichten hinteres Paar noch ungeklärt. Der Prüfablauf
lässt deshalb zunächst LF/LR/RF parallel und anschließend RR fahren. Reine
Fahrzeit etwa193,5→80,9s; alle Quellwege unverändert. Noch keine Hardwareausführung.

## Fünf Fotos und Oberfläche

```bash
bash src/multi_arm_manipulation_UWA/scripts/object_capture.sh
# Ohne Oberfläche, ausdrücklich eine Kameraaufnahme:
bash src/multi_arm_manipulation_UWA/scripts/object_capture.sh --capture-only \
  --output "$UWA_WS/setup/digitization/NEUE_SITZUNG/acquisition"
```

Englische Oberfläche mit **CAPTURE ALL FIVE**, fünf Bildfeldern, deutlich sichtbaren
Aktions-/Fehlertexten, Bildalter und Snapshot-/STALE-Kennzeichnung. Bei wenig
Fensterhöhe scrollen nur die Kamerafelder; Aktionsstatus und Bedienelemente bleiben
erreichbar. Dieser Aufruf darf erst verwendet werden, wenn die Kameras frei sind.
Er startet keine Roboter, keine Treiber und keine Armbewegung.

- Auswahl: vier Wrist-Kameras plus OAK. Native2592×1944 bzw.8000×6000, keine
  Belichtungssynchronität. Beide festen40mm-Boards werden getrennt erkannt.
- Profil `config/digitization/five_camera_capture.yaml`: LF245/LR406/RF435/RR388,
  OAK116. **Aufnahmeprofil, keine Kalibrierung.** Originaleinstellungen und
  bestätigte Rückstellung bleiben erhalten; Kamera-Worker/LED-Nutzung werden
  über die vorhandenen Pfade geteilt.
- Vor Fotostart mindestens0,5s frische ruhige Telemetrie aller vier Arme.
  Während der Aufnahme kontinuierliches JointState-Protokoll mit Original-
  ROS-Stempeln, Host-Empfang und Geschwindigkeiten. Bewegung, hohe Geschwindigkeit
  oder veraltete Telemetrie verweigern die Bestätigung eines statischen Satzes.
  `all_captured` beschreibt nur gespeicherte Fotos, `stationary_set_confirmed`
  separat den Audit. Dies ist keine überwachte Arm-Stoppfunktion.
- Fotos bei einem später erkannten Fehler bleiben zur Diagnose erhalten. Kein
  automatisches Bewegen, Rückfahren oder Aktivieren von Kalibrierprofilen.

Rohdaten/Sitzungen unter `setup/digitization/`, nicht im Git. Die ursprüngliche
Dreikamera-App und ihr mobilesA4-Board bleiben der bisherige Standardaufruf.

## Übergabe an die Rekonstruktion

`digitize_box --capture-set ...` akzeptiert auch die fünf gespeicherten Kameras.
Fehlende passende Intrinsics führen zu einer ausdrücklich nicht metrisch nutzbaren
Kamera, niemals zur Übernahme fremder VGA-/HD-Parameter. Ein nicht bestandener
Stillstandsaudit wird vor metrischer Vorbereitung abgewiesen.

Bei zwei Referenzboards schätzt dasselbe OAK-Foto beide Boardposen. Damit lässt
sich eine Wrist-Beobachtung des linken Boards in den gemeinsamen rechten
Boardframe überführen:
`T_cam_right = T_cam_left · inv(T_oak_left) · T_oak_right`.
Keine nominellen Tischabstände/FK als Ersatz verwenden. Fehlt die beobachtete
Brücke, bleiben entsprechende Fotos nicht metrisch nutzbar. Qualität/Hash und
Auflösungs-/Fokusbindung der vorhandenen Profile bleiben erhalten.

Danach: unterstützten parametrischen Fit wiederholen, denselben gespeicherten
Datensatz später mit COLMAP/OpenMVS und MASt3R/VGGT vergleichen. Noch keine dichte
oder gelernte Rekonstruktion installiert oder auf dem neuen Karton ausgeführt.

## Nachweis am neuen Karton, 12.11.2026

Nutzer bestätigt: neuer größerer Karton mittig zwischen beiden Tischen, Unterseite
auf Tischhöhe, grob40×30×20cm. Frisches OAK-Foto18:20AWST, **ein einzelner**
nativer8K-Frame bei116. Rechte Board-PnP mit24ChArUco-Ecken,1,33nativePixelRMS.
Assistierter Sechspunktfit: ca.43,9×34,6×15,8cm,4,38px Punkt-RMS im1600px-Prüfbild.
Kein Genauigkeitsnachweis. Entwurfsvolumen ca.54,5×43,7×27cm.

Enger Suchbereich verworfen: das vergrößerte Volumen passte für die linken Kameras
nicht vollständig ins Bild. Erweiterter Bereich0,6–1,05m und0,35–0,65m Höhe über
Objektmitte fand fünf gemeinsame Ansichten und15Zusatzansichten. Nach erneuter
reiner Zustandslesung18:35:48AWST bestätigt:19serielle Wege,1963geprüfte Punkte,
ca.139s Grundpositionierung und55s Zusatzwege, ohne Foto-/Stillstandszeiten.
Eine Zusatzansicht wurde verworfen. Aktuellster Entwurf `new_carton_plan_current/`.
Das ist ein Modellbefund, kein realer Sicht-/Fahrnachweis. Früherer Entwurf für
den alten Karton auf dem rechten Tisch ist für diesen Aufbau überholt.

Daten: `setup/digitization/five_camera_design_20261112/` mit OAK-Verweis,
Annotation/Overlay, Schätzung, verworfenen und aktuellen Entwürfen. Kein neuer
Wrist-Fünfersatz und keine reale Scan-Armfahrt. Build und35gezielte Tests einschließlich Parkregressionen PASS;
zusätzlich echte reine JointState-Leseprüfung: alle vier Arme frisch/ruhig,
keine Kommandos, Auditdaten unter `read_only_audit/`. Qt-Oberfläche mit deutlich
gekennzeichneten synthetischen Snapshots offline gerendert/geprüft.
