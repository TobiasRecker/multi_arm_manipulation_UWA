# Vier Armkameras plus OAK für Objektrekonstruktion

Stand: 13.11.2026. Nutzerziel: ein Objekt in einem gemeinsamen Tischbereich mit
vier Wrist-Kameras und OAK fotografieren, optional mit zusätzlichen Ansichten
nach kleinen Kamerabewegungen. Konzept und Literaturbewertung. Die erste Implementierung ist inzwischen unter
[OAK zuerst und Fünfkamera-Aufnahme](object_scan.md) dokumentiert. Am13.11. erreichten alle vier Arme ihre fünf realen Scanstellungen;
25/25 Bilder sind bestätigt; die letzte OAK-Gruppe wurde nach dem freigegebenen
OS1.47-Update im Stillstand ergänzt. [Ergebnis und Grenzen](parallel_object_scan.md).
Ein erster [CAD-Entwurf des neuen Kartons](carton_multiview_2026-11-13.md) ist
inzwischen exportiert: ca.404×342×163mm, sichtbare Ausschnitte/Fototexturen,
20metrische Fotos, zehn zurückgehaltene Prüfbilder; keine metrische Freigabe.

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

## Historischer Vorbereitungsstand vom12.11. vor dem vollständigen Scan

Der Nutzer hat den Beginn beauftragt und den Aufbau korrigiert: neuer größerer
Karton **zwischen beiden Tischen**, Unterseite auf Tischhöhe, grob40×30×20cm.
Die erste [Softwarestufe](object_scan.md) verbindet OAK-Foto, assistierte grobe
Geometrie, reserviertes Planungsvolumen, gemeinsame Ansichten und Fünfkamera-GUI.
Neue Wege sind reine Prüfartefakte ohne Hardware-Ausführung.

- OAK-Einzelbild real aufgenommen; grobe Maße ca.44×35×16cm, nicht abschließend
  validiert. Planungsvolumen etwa55×44×27cm. Weitere Geometrie aus mehreren Fotos.
- CaptureRig unterstützt explizite Kameralisten; Dreikamera-Standard erhalten.
  Für fünf Kameras kontinuierlicher Stillstandsaudit, beide Tischboard-Identitäten.
- Einige passende native-HD-Kalibrierungen sind separat beziehungsweise noch in
  Arbeit. Aufnahmen ohne passende K/D bleiben für metrische Fits ausgeschlossen.
- Der Planer fand im erweiterten Suchbereich gemeinsame Modellansichten und
  geprüfte Wege; noch kein realer Fünfkamera-Datensatz. Neue reale Wege brauchen
  frischen Zustand und Durchsicht. Laufende Kalibrierreihen erhalten.
- Lokal Intel-Grafik, kein erkanntes CUDA-Gerät. COLMAP Sparse auf CPU möglich,
  dessen eigene dichte Rekonstruktion benötigt CUDA. Noch keine Lernmodelle
  installiert oder ausgeführt.
  [COLMAP ohne CUDA](https://colmap.github.io/faq.html#available-functionality-without-gpu-cuda).
- `five_camera_scan_design.yaml` bleibt das ursprüngliche nicht ausführbare
  Konzept. Der implementierte Planer verwendet separat erzeugte `scan_geometry.yaml`.
