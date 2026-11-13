# FoundationPose auf titanpc

Stand: 2026-11-13. Isolierter Versuch auf der gemeinsam genutzten Workstation
`titanpc`/`192.168.2.137`, erreichbar über WLAN und `ssh uwa-ubuntu22`.
Installation und Prüfergebnisse werden unten nachgeführt.

## Ziel und Zusammenhang

Bekannte metrische Assets sollen aus Kamerabildern als `T_camera_object`
wiedergefunden werden: statische Lokalisierung vor Manipulation und dynamische
Verfolgung. Der [CPU-Tracker](object_tracking.md) bleibt erhalten. Beim neuen
[PTFE-/Aluminiumobjekt](ptfe_l_assembly.md) scheitert dessen Texturwiedererkennung
bisher; FoundationPose nutzt zusätzlich Geometrie/Tiefe und wird getrennt geprüft.
Ein bestandener Demolauf ist keine nachgewiesene Erkennung unserer Assets.

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

## Grenze zur echten UWA-Zelle

Die offizielle modellbasierte API benötigt metrisches Mesh, RGB, dazu passende
Tiefe und Intrinsics sowie zur Initialisierung eine Objektmaske. Der vorhandene
OAK-HQ-Tiefenmodus liefert rektifizierte Mono-Tiefe, noch keine RGB-ausgerichtete
Tiefe. Er darf nicht einfach pixelweise mit RGB kombiniert werden. Wrist-Kameras
liefern für diesen Versuch ebenfalls noch keinen geprüften RGB-D-Eingang.

Nach erfolgreichem Demolauf: passende OAK-RGB-D-Aufnahme und Objektmaske prüfen,
unsere Meshes im unveränderten Assetframe zuführen, lokale/remote Zeiten und
Bildalter über WLAN messen. Welt-/Roboterpose benötigt zusätzlich eine zeitlich
passende Kameraregistrierung. Weder Demolauf noch niedriger Pixelrestfehler sind
Manipulationsfreigabe oder Nachweis absoluter Millimetergenauigkeit.

## Prüfergebnisse

Installation läuft; noch kein FoundationPose-Inferenzerfolg behauptet.
