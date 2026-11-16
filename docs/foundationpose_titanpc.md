# FoundationPose auf titanpc

Stand: 2026-11-16. Isolierter Versuch auf der gemeinsam genutzten Workstation
`titanpc`/`192.168.2.137`, erreichbar über WLAN und `ssh uwa-ubuntu22`.
FoundationPose ist installiert; offizielle RGB-D-/Bewegungsdemo und erster
realer statischer Kartonversuch bestanden (visuelle Konsistenz, keine Messfreigabe).
Alle eigenen Rechenprozesse sind beendet.

## Ziel und Zusammenhang

Bekannte metrische Assets sollen aus Kamerabildern als `T_camera_object`
wiedergefunden werden: statische Lokalisierung vor Manipulation und dynamische
Verfolgung. Der [CPU-Tracker](object_tracking.md) bleibt erhalten. Beim neuen
[PTFE-/Aluminiumobjekt](ptfe_l_assembly.md) scheitert dessen Texturwiedererkennung
bisher. FoundationPose ist ein eigener GPU-Testpfad; der reale Avocado-Karton
wurde am16.11. mit manueller Startmaske lokalisiert. PTFE und bewegter realer
Karton sind noch nicht GPU-geprüft. Der bestehende ROS-Tracker bleibt unverändert.

## Isolation und Ressourcen

- Nutzerauftrag: Rechenleistung nutzen, bestehende Workstation-Nutzung erhalten.
- TITAN RTX,24GiB VRAM; Ubuntu22.04.5; Treiber570.211.01; Toolkit12.3.
  `nvidia-smi` nennt12.8 als Treiberfähigkeit, nicht als installiertes Toolkit.
- Systempartition zu Beginn nur5,5GiB frei. Alle großen eigenen Dateien unter
  `/media/ubuntu22/RAID1_L/uwa-foundationpose-ubuntu22` (anfangs525GiB frei).
- Eigene Python3.11-Conda-Umgebung unter `envs/foundationpose`. Bestehende
  Conda-Umgebungen bleiben erhalten. Kein `sudo`, APT, Treiberwechsel,
  Gruppenwechsel, Docker-Daemon-Neustart, Boot-/Shellprofilwechsel.
- Docker ist installiert, aber der Benutzer darf seinen Socket nicht öffnen.
  Deshalb eigene Umgebung statt Änderung von Docker-Berechtigungen.
- Build maximal4Jobs, CPU-Bibliotheken4Threads und `nice10`. CUDA nur GPU0;
  Test begrenzt den PyTorch-Allocator auf45% VRAM. Das begrenzt weder jeden
  Fremdallocator noch garantiert es störungsfreie gleichzeitige GPU-Auslastung.
  Vor Wiederholungen aktuelle Last prüfen; Test endet nach begrenzter Bildzahl.
- Cache-, Paket- und temporäre Verzeichnisse liegen im eigenen Arbeitsordner.
  Kein öffentlich erreichbarer Dienst, ROS-/Roboternetz oder Kamerafernzugriff.

## Reproduzierbare Bestandteile

Offizieller Quellcode: [NVlabs/FoundationPose](https://github.com/NVlabs/FoundationPose),
Commit `a1b694b83e633c2cb6115b9063d940a687759392`.
Upstream-Lizenz und Modellquellen bleiben im separaten Checkout; Modelle werden
nicht in dieses Repository kopiert.
Ein lokaler Einzeilenpatch leitet den hartcodierten `/tmp`-Mesh-/Materialexport
auf den privaten `TMPDIR` um; protokolliert unter `logs/upstream-local.patch`.
PyTorch2.5.1+cu121, PyTorch3D0.7.8 und nvdiffrast0.3.3 sind in der eigenen
Umgebung installiert. Vollständige Versionen: `logs/pip-freeze.txt`.

- `tools/foundationpose_titanpc_env.bash`: Umgebung nur für eigenen Unterprozess.
- `tools/foundationpose_titanpc_constraints.txt`: eigene Versionsgrenzen.
- `tools/foundationpose_titanpc_install.sh`: Python-Abhängigkeiten und native
  Erweiterungen; setzt bereits angelegte eigene Python-/Torch-Umgebung voraus.
- `tools/foundationpose_download_demo.py`: zwei offizielle Modelle und
  Mustard-Demo aus den vom Upstream verlinkten öffentlichen Drive-Ordnern,
  ohne Anmeldung/Cookies; Downloadhashes werden protokolliert.
- `tools/foundationpose_smoke.py`: begrenzte Register-/Trackingprüfung ohne GUI,
  Originalmodellframe/Metereinheit, Poseprüfung, Overlay und Laufzeitbericht.
  Annotierte Posen erst nach Schätzung zum Vergleich lesen, niemals initialisieren.

Die Werkzeuge liegen remote im eigenen Unterordner `tools/`; Logs unter `logs/`,
Testergebnisse unter `results/`. Keine Geheimnisse in Dokumentation oder Git.

## Benutzen

Aus `~/UWA_ws` auf diesem Arbeitsplatz:

```bash
# Aktuelle GPU-Nutzung, Platz und vorhandene Berichte lesen.
bash src/multi_arm_manipulation_UWA/scripts/foundationpose_remote.sh status

# Kurzer offizieller RGB-D-Test: zwölf Bilder, anfangs ruhender Gegenstand.
bash src/multi_arm_manipulation_UWA/scripts/foundationpose_remote.sh smoke

# Hundert Bilder einschließlich Anheben/Bewegen in der gespeicherten Demo.
bash src/multi_arm_manipulation_UWA/scripts/foundationpose_remote.sh smoke-motion

# Bereits übertragenes, gehashtes reales Kartonpaket,640×480/achtBilder:
bash src/multi_arm_manipulation_UWA/scripts/foundationpose_remote.sh input carton_20261116_111619_640
```

Die offiziellen Demos verwenden jeden dritten Frame, der Eingabetest jeden
Frame. Alle verwenden eigene Ausgabeordner, einen
gemeinsamen Versuch-Lock und maximal10min Laufzeit. Sie öffnen keine lokale
oder ferne Kamera und starten keine Roboter-/ROS-Dienste. Erster Start kann
zusätzliche CUDA-Kernels bauen. `DONE` wird erst nach erfolgreichem Abschluss
ausgegeben. Es wird kein dauerhafter Rechendienst eingerichtet.

## Grenze zur echten UWA-Zelle

Die offizielle modellbasierte API benötigt metrisches Mesh, RGB, dazu passende
Tiefe und Intrinsics sowie zur Initialisierung eine Objektmaske. Der neue
OAK-RGB-D-Modus liefert diese Bildgeometrie seit16.11. Der separate ältere
HQ-Tiefenmodus bleibt rektifizierte Mono-Tiefe und darf nicht einfach pixelweise
mit RGB kombiniert werden. Wrist-Kameras
liefern für diesen Versuch ebenfalls noch keinen geprüften RGB-D-Eingang.

Realer Offlinepfad für den Karton ist jetzt geprüft; noch offen sind laufender
WLAN-Transport, Bildalter/LOST-Verhalten und echte Bewegung. Die Welt-/Roboterpose benötigt eine zeitlich
passende Kameraregistrierung. Weder Demolauf noch niedriger Pixelrestfehler sind
Manipulationsfreigabe oder Nachweis absoluter Millimetergenauigkeit.

## Realer Kartonversuch16.11.2026

- Nutzer stellt bekannten Avocado-Karton neben studentischen Roboter und
  bestätigt ruhende Aufnahme. Neue Pose: Karton steht auf einer Seite.
  Acht originale1280×960-RGB-D-Paare unter
  `setup/oak4/rgbd/20261116-111619-rgbd-5a8d0ae9/`.
- Initialmaske: vom Assistenten am ersten Farbbild visuell nachgezeichneter
  sichtbarer Umriss einschließlich Ausschnitt; keine automatische Detektion
  oder unabhängige Ground Truth. Polygon/Bildhash bleiben gespeichert.
- `foundationpose_prepare_input.py` prüft Asset-/Capturehashes, Metereinheit,
  Ausgabe-K, Formate und Maskenzuordnung. Unverändertes GLB-Assetframe,292
  Dreiecke, Materialien in ein2048×4096-Texturatlas exportiert; OBJ-Rückimport
  prüft Geometrie/Bounds. `reference_pose` aus asset.json wird nicht verwendet.
- Erster1280×960-Lauf erreicht45%-Allocatorlimit; eigener Prozess beendet,
  Fehlerlog erhalten. Danach Arbeitsbilder640×480, RGB Lanczos, Tiefe/Maske
  nearest-neighbour, keine Tiefenfüllung. Ausgabe-K mit Pixelzentrumkonvention
  angepasst: sx=sy0,5 und Verschiebung−0,25px. Originaldaten unverändert.
- Acht-Frame-Lauf erfolgreich:1,623s globale Registrierung,18,806ms mediane
  Trackingkernzeit,6,55s Gesamtprozess aufGPU einschließlich Start/Datei-I/O/
  Auswertung. Weder Live-FPS noch WLAN-Ende-zu-Ende-Latenz gemessen.
- Endliche starre Kameraposen, projizierte Box und Textur-Rückrender visuell
  plausibel. Startmasken-IoU0,913; medianer Eingabe-Tiefenrest7,08mm. Das sind
  Konsistenzwerte am zur Schätzung verwendeten Material, keine absolute
  Genauigkeit. Geschätzte Schwankung über0,7s≤1,97mm/0,29° ebenfalls kein
  unabhängiger Genauigkeits- oder Bewegungsnachweis.
- PyTorch4326MiB maximal belegt/5068MiB reserviert, Limit unverändert45%.
  Eigene Prozesse beendet, GPU wieder175MiB/0%. Paket-/Conda-/Shell-/Docker-
  Metadaten vor/nach dem heutigen Versuch identisch; kein Systemeingriff.
- Kamera-Lease danach frei; keine UR-/ROS-/RViz-/Kalibrierprofiländerung.
 38OAK-Tests/9Subtests sowie3Exporttests bestanden: fremder Maskenframe,
  Millimeter/Nullwerte bei Verkleinerung und Unabhängigkeit vom Szenenposefeld.

Lokale Daten: `setup/tracking/foundationpose_carton_20261116/`, darin
`input_640/`, `result_640/report.json`, `visual-review.json`, Box-/Textur-Overlays
und Workstation-Audits. Erfolg remote:
`results/carton_20261116_111619_640_20261116T032608Z_2990307/`.
Logs lokal `setup/logs/foundationpose-carton-real[-640]-20261116.log`.
Werkzeuge: `foundationpose_prepare_input.py`, `foundationpose_render_result.py`,
CLI `foundationpose_remote.sh input NAME`. Es wird kein permanenter GPU-Dienst
oder neuer ROS-Backend aktiviert. Reale Bewegung, Verdeckung, Wiederfinden
und unabhängige metrische Prüfung stehen aus.

## Vorgeschlagener Weg zu realen Eingaben, 2026-11-16

Nach der folgenden Bestandsprüfung hat der Nutzer Schritt1 beauftragt. Dieser
ist jetzt umgesetzt: [OAK-RGB-D-Modus](../../oak_camera_calibration/OAK4_RGBD.md),
erster Datensatz mit studentischem Roboter statt Karton erfolgreich. Acht
entzerrte1280×960-Paare, maxZeitdifferenz1,727ms; K und Formate geprüft.
Offline-Boardprüfung jetzt ebenfalls durchgeführt:16Fit-/8Prüfecken,
maxPrüf-RMS0,3222px, aber SDK-Tiefe gegenüber RGB-Boardebene median+11,05mm.
Nutzer-Linealmessung5Felder200mm passt zum Nominalmaß. Ursache/absolute
Genauigkeit bleiben offen; weitere mobile Boardansichten vorgeschlagen.
Daten unter
`setup/oak4/rgbd/20261116-102913-rgbd-fa320e7a/`. Ein bekanntes Mesh wird erst
für die spätere Objektpose benötigt. Weitere Planstufen sind noch Empfehlungen.

GPU-/Demoergebnisse oben stammen vom13.11., nicht aus einer
erneuten Erreichbarkeitsprüfung. Zuerst eine feste OAK verwenden; vorhandene
Wrist-/Hand-Auge-Kalibrierungen müssen für die reine Kamerapose nicht neu entstehen.

| Eingabe | Vorhanden | Nächster Schritt |
|---|---|---|
| Metrisches Objektmodell | Karton-/PTFE-Assets mit festem Frame, teilweise vereinfachter Geometrie | Meter-Mesh übernehmen, Kontrollmaße prüfen, Ursprung erhalten |
| RGB und Tiefe | RGB-Vorschau und separater Mono-HQ-Tiefenmodus | Gemeinsame SDK-Pipeline: RGB entzerren, Stereo-Tiefe in diese RGB-Perspektive reprojizieren |
| Intrinsics und interne Sensorlage | OAK-Werkskalibrierung und auslesbare Ausgabe-K | Tatsächliche K der gewählten Ausgabe/Fokus speichern und am Board prüfen |
| Initialmaske | Für UWA-Objekte noch nicht als FoundationPose-Eingabe angelegt | Im ersten Farbbild einmal sichtbaren Objektumriss markieren; Automatisierung später |
| Zeitbezug/Frische | Gerätezeiten und Bildalter teilweise vorhanden | RGB-/Tiefenpaare gruppieren, Zeitdifferenz messen, verspätete Paare abweisen |
| Pose zur Roboterbasis | Vorläufig akzeptierte OAK-Weltregistrierung | Für Greifen gesondert über gemeinsame Boardbeobachtung und gültige Kamera-/Roboterkette unabhängig prüfen |

Luxonis dokumentiert für RVC4 `StereoDepth → ImageAlign → Sync`; RGB wird
mittels `enableUndistortion=True` angefordert. ImageAlign verwendet die interne
Sensor-Kalibrierung, Sync gruppiert anhand Zeitstempeln. Das ist kein Nachweis
gleichzeitiger Belichtung und noch keine Kalibrierung zur Roboterbasis.
Nicht einfach aktuelle, getrennte HQ-RGB-/HQ-Tiefenbilder zusammenlegen.
Die16Frame-HQ-Fusion bleibt für ruhende Szenen; dynamisch einzelne passende Paare.

Vorgeschlagene Reihenfolge:

1. Eigenen opt-in-RGB-D-Aufnahmemodus an vorhandene Kamera-Lease anbinden;
   bestehende Kameranutzer erhalten. Ein moderates Profil testen, z.B.
   1280×960RGB und5–10fps; das ist ein Startvorschlag, keine gemessene Zusage.
2. Ein statisches Paket mit RGB, RGB-ausgerichteter Z-Tiefe, Gültigkeitsmaske,
   Ausgabe-K, Fokus, Framekonvention, Sequenzen und Zeitstempeln speichern.
   Tiefeneinheit explizit; Factory-D nicht auf bereits entzerrte Bilder anwenden.
3. Kantenüberlagerung, Board-Reprojektion und Tiefe an einer vermessenen
   Referenz prüfen. Fehlende Tiefe auf glatten/weißen/reflektierenden Teilen
   sichtbar lassen. Nur bei unzureichender Prüfung gezielt nachkalibrieren.
4. Startmaske manuell zeichnen und vorhandenes Meter-Mesh zuführen. Zuerst
   gespeicherten Karton-Datensatz auf titanpc auswerten, danach PTFE. Modell
   in Bildern/Tiefe zurückprojizieren und Wiederholungen sowie unabhängige
   Kontrolllagen prüfen; deren Posen niemals zur Schätzung initialisieren.
5. Nach statischem Erfolg kurze Bewegungs-/Verdeckungssequenz aufnehmen und
   offline prüfen. Danach erst Live-Übertragung über WLAN mit gemessenem
   Ende-zu-Ende-Alter, Verwerfen alter Bilder und LOST/STALE-Ausgabe anbinden.
6. Für Roboterkoordinaten die zusätzliche OAK→Basis-Registrierung unabhängig
   prüfen, z.B. gemeinsames Board in OAK und gültig kalibrierter Wrist mit
   zeitlich passenden Gelenken. Vorläufige Weltanker nicht als Messwahrheit
   verwenden; keine automatische Armfahrt aus diesem Plan.

Software kann Kalibrierdaten auslesen, Aufnahmepaare bilden, exportieren und
auswerten. Physisches Bereitstellen des Objekts/Boards und unabhängige
Kontrollmaße/-lagen benötigen Bedienerarbeit bzw. vorhandene Messmittel.

Offizielle Quellen: [RVC4 Depth Align](https://docs.luxonis.com/software-v3/depthai/examples/image_align/depth_align),
[ImageAlign](https://docs.luxonis.com/software-v3/depthai/depthai-components/nodes/image_align),
[Sync](https://docs.luxonis.com/software-v3/depthai/depthai-components/nodes/sync),
[FoundationPose-Demo](https://github.com/NVlabs/FoundationPose/blob/main/run_demo.py).

## Prüfergebnisse

- CUDA-Matrixrechnung auf TITAN RTX/Compute7.5 bestanden.
- Native Erweiterungen gebaut; `pip check`: keine verletzten Abhängigkeiten.
- Zwölf-Frame-Demo PASS: eine globale Initialisierung, elf Tracking-Schritte;
  endliche starre Posen im originalen Meshframe. Initialisierung2,683s,
  Trackingkern median24,57ms; Gesamtprozess18,63s einschließlich Import,
  Modellstart, Auswertung und Bildausgabe. Keine WLAN-/Live-Ende-zu-Ende-FPS.
- PyTorch maximal4423MiB belegt/5058MiB reserviert, eigener Prozess beendet.
- Anfangsmaske: projizierte Silhouetten-IoU0,905; Tiefenrest auf Überlappung
  ca4,65mm. Das ist Konsistenz mit Eingabedaten, keine unabhängige Genauigkeit.
  Nur erste Maske vorhanden; für Folgeframes wird das Fehlen ausdrücklich
  markiert und der Tiefenvergleich kann Verdeckungen einschließen.
- Zusätzliche Bewegungsprüfung PASS:100Bilder, Originalindizes0..297 in
  Dreierschritten, eine Initialisierung und99Tracking-Schritte. Initialisierung
  1,699s, Trackingkern median24,61ms, Gesamtprozess37,82s einschließlich
  Ein-/Ausgabe/Auswertung. Die Aufnahme zeigt Anheben/Drehen und Annäherung
  eines zweiten Roboters. Bilder bei120/297 visuell mit passender Box geprüft.
  Geschätzte Bewegung bis540mm/76°; keine unabhängige Weg-/Winkelmessung.
- Die zwölf Startbilder zeigen noch überwiegend Stillstand; deren getrennte
  Prüfung allein wäre kein Nachweis des Verfolgens eines bewegten Gegenstands.
  Für die Bewegungsprüfung fehlen ebenfalls annotierte6D-Ground-Truth-Posen;
  der mediane Tiefenrest1,91mm ist nur Eingabekonsistenz, keine Genauigkeitsfreigabe.
- Vorher-/Nachherhashes von Paketdatenbank, bestehenden Conda-Verläufen und
  Shell-/Dockerkonfigurationen identisch. Nach Test GPU wieder175MiB/0%,
  Systempartition weiterhin5,5GiB frei. Eigener Ordner ca9,3GiB.

Lokale Nachweise: `setup/tracking/foundationpose_titanpc_20261113/`
(`report.json`, zwei Overlays, Paketversionen, Modellhashes, Metadatenvergleich).
Bewegungsbericht und zwei zusätzliche Overlays im Unterordner `motion/`.
Vollständige lokale Testlogs: `setup/logs/foundationpose-smoke-20261113.log`
und `setup/logs/foundationpose-motion-20261113.log`.
Remote-Erfolge: `results/mustard_20261113T083433Z_171062/` und
`results/mustard_100_20261113T083738Z_173849/`.
Vorheriger Lauf blieb wegen fehlender optionaler Folgebildmaske in der
zusätzlichen Auswertung unvollständig; Bericht/Log erhalten, Prüfung korrigiert.
