# Vier Armkameras plus OAK für Objektrekonstruktion

Stand: 12.11.2026. Nutzerziel: ein Objekt in einem gemeinsamen Tischbereich mit
vier Wrist-Kameras und OAK fotografieren, optional mit zusätzlichen Ansichten
nach kleinen Kamerabewegungen. **Recherche und Konzept, kein ausführbarer Fahrplan.**

## Nutzen und gemeinsame Sicht

Vier Blickrichtungen können mehr Außenflächen und Innenwände erfassen. Zunächst
müssen Erreichbarkeit, Bildausschnitt und Verdeckungen für denselben Objektbereich
geprüft werden. Die bisherigen Vierarm-Designposen betrachten jeweils das eigene
Tischboard; sie beweisen keine gemeinsame Sicht auf ein Objekt. Der bisherige
rechte Boardbereich ist nur eine erste Designannahme.

Zuerst eine Stellung je Wrist plus OAK: **fünf Ansichten**. Anschließend insgesamt
3–5 Stellungen je Wrist plus eine feste OAK-Perspektive: **13–21 unterschiedliche
Blickpunkte**. Fünf Aufnahmerunden ergeben zwar 25 Fotos, aber die OAK wiederholt
ihre Perspektive. Verdeckte Unterseiten brauchen einen zweiten Aufbau. Einfarbige
Pappe bietet wenig Bildtextur; mehr Fotos allein garantieren keine bessere Geometrie.

## Kleine Bewegungen und Aufnahme

Wenige Zentimeter TCP-Verschiebung beweisen keine Kollisionsfreiheit. Der gesamte
Gelenkweg einschließlich Ellbogen, Handgelenken, Greifern und Kameras ist gegen
andere Arme, Tisch und Objekt zu prüfen. IK-Zweigwechsel vermeiden; vorhandene
Kollisionsprüfungen und native UR-Stoppfunktionen erhalten. Nicht modellierte
Kabel werden durch einen Planer nicht automatisch erfasst.

Bei 50 cm Objektabstand erzeugen 2 cm seitliche Verschiebung etwa 2,29° und 5 cm
etwa 5,71° Richtungsänderung. Das hilft der Parallaxe, erschließt aber kaum eine
verdeckte Rückseite. Zusätzliche Höhen und Blickrichtungen sind deshalb zu prüfen.
Der Bildausschnitt folgt Objektgröße und tatsächlicher Kameraprojektion; gerade
der 52-cm-Karton passt nicht bei jedem Kameraabstand vollständig ins Bild.

Für die erste Umsetzung: Arme nacheinander positionieren, für Zusatzansichten
zunächst jeweils einen Arm bewegen und vor der Aufnahme gemessenen Stillstand
aller Arme bestätigen. Gemeinsame Anforderung der Fotos bedeutet keine synchrone
Belichtung. Objekt und Referenz müssen während der Aufnahme ruhen.

## Verfahren aus der Literatur

- **COLMAP und OpenMVS:** geometrische Vergleichsbasis mit Kameraparametern,
  bekannten Posen und gegebenenfalls Bündelausgleich. OpenMVS verarbeitet Posen
  und dünne Punktwolken zu dichten Oberflächen und texturierten Meshes.
  [COLMAP](https://colmap.github.io/faq.html),
  [OpenMVS](https://github.com/cdcseacave/openMVS).
- **DUSt3R / MASt3R:** gelernte Punktkarten und Bildzuordnung; MASt3R ergänzt
  dichte Merkmale für robustere Korrespondenzen auch bei stark verschiedenen
  Ansichten. Kandidat für weniger manuelle Punktzuordnung, hier noch ungetestet.
  [DUSt3R](https://arxiv.org/abs/2312.14132),
  [MASt3R](https://arxiv.org/abs/2406.09756),
  [Implementierung](https://github.com/naver/mast3r).
- **VGGT:** schätzt Kameraparameter, Tiefen-/Punktkarten und Bildpunktspuren;
  offizieller COLMAP-Export mit optionalem Bündelausgleich. Kandidat für eine
  weitere Initialisierung und Vergleichsrekonstruktion. Gelernte Tiefe ist
  bildbasiert, aber kein Nachweis metrischer Richtigkeit.
  [Implementierung](https://github.com/facebookresearch/vggt).
- **NeRF / Gaussian Splatting:** interessant für Ansichtsynthese und Darstellung.
  Ein Darstellungsmodell ist noch kein editierbarer, maßhaltiger CAD-Körper.
  Zusätzliche Mesh-Exporte sind möglich; anschließend bleibt die CAD-Anpassung.
  [Nerfstudio-Geometrieexport](https://docs.nerf.studio/quickstart/export_geometry.html).

Die unabhängig bewegten Wrist-Kameras sind **kein starres Kamerarig**. Intrinsics
je physischer Kamera führen, Posen dagegen je Aufnahme aktualisieren beziehungsweise
mit passenden Messprioren optimieren. COLMAPs Rigmodell setzt feste relative
Sensorposen voraus: [Rig-Dokumentation](https://colmap.github.io/rigs.html).

## Empfohlene Pipeline und Prüfung

`Fotos → Objektmasken → Punktwolke → Oberflächenmesh → parametrischer CAD-Fit`

Originale, passende K/D und Bildgrößen, Fokus, Zeitstempel, Telemetrie, Referenzmaßstab
und Qualitätskennzeichnung speichern. Kameraposen bevorzugt aus sichtbaren
metrischen Referenzen, alternativ aus zeitlich passender FK und Hand-Auge-
Kalibrierung bestimmen. Keine alten, ungemessenen Roboterposen übernehmen.
Objektmasken schließen Arme und Hintergrund von der Rekonstruktion aus;
Boardreferenzen separat zur Posenschätzung nutzen.

Den Karton zunächst mit mehr Ansichten und bestehendem CAD-Fit auswerten. Denselben
unveränderten Datensatz mit klassischer Geometrie und später MASt3R oder VGGT
vergleichen. Vorab zurückgehaltene Ansichten, Boardmaßstab und reale Kontrollmaße
prüfen Geometrie und Skalierung. Für einfache Objekte bleibt eine Ebenen-/Quader-
oder andere parametrische Anpassung sinnvoll. Ein Mesh wird nicht automatisch
zu bearbeitbaren CAD-Flächen.

## Lokaler Stand

- Alle vier Wrist-Kameras haben inzwischen einen nachgewiesenen nativen
  HD-Aufnahmepfad. Der bestehende CaptureRig-Code verwaltet noch zwei rechte
  Wrist-Kameras plus OAK; fünf Kameras sind dort noch nicht implementiert.
- HD-Kalibrierungen rechts hinten und links vorne laufen beziehungsweise warten
  auf Fortsetzung. Passende K/D und Fokus nicht als bereits aktiviert voraussetzen.
  Laufende Serien werden für dieses Konzept nicht unterbrochen.
- Lokal ist Intel-Arrow-Lake-Grafik erkannt, kein NVIDIA/CUDA-Gerät. COLMAPs
  Sparse-Schritte können auf CPU laufen, seine eigene dichte Rekonstruktion
  benötigt CUDA. Schwere Lernverfahren zunächst begrenzt testen oder auf einem
  geeigneten GPU-Rechner ausführen.
  [COLMAP ohne CUDA](https://colmap.github.io/faq.html#available-functionality-without-gpu-cuda).
- `config/digitization/five_camera_scan_design.yaml` ist ein nicht ausführbares
  Designprofil ohne Consumer. YAML und Ansichtszähler wurden geprüft.
- Noch keine gemeinsamen Zielposen oder Verbindungswege berechnet/geprüft,
  keine neue Kameraaufnahme oder Armbewegung, keine Modellinstallation und
  keine dichte oder gelernte Rekonstruktion für diese Recherche ausgeführt.

Nächster Umsetzungsschritt: gemeinsamen Scanbereich festlegen, passende Kamera-
profile und aktuellen Vierarmzustand einlesen, dann Grund- und Zusatzposen mit
vollständigen Verbindungswegen prüfen und in RViz zur Durchsicht darstellen.
