# FoundationPose auf gemeinsamer NVIDIA-Workstation

- Status: **abgeschlossen – isolierte Installation und Bewegungsdemo geprüft**,
  2026-11-13, Hauptagent dieses Gesprächs.
- Nutzerauftrag: FoundationPose auf erreichbarer WLAN-Workstation prüfen und
  möglichst isoliert zum Laufen bringen; andere Nutzer/Umgebungen erhalten.
- Kontext: bekannte Karton-/PTFE-Assets, statische6D-Lokalisierung und
  dynamischesTracking. CPU-Prototyp bleibt erhalten; keine Roboteraktionen.
- Rechner titanpc: TITAN RTX24GiB, Ubuntu22.04, Treiber570.211.01,
  CUDA-Toolkit12.3. Momentaufnahme: kaum GPU-Last,21GiB RAM verfügbar.
- Systempartition nur5,5GiB frei. Docker installiert, Benutzer ohne Socket-
  Zugriff; keine Gruppen-/Daemon-/Treiberänderungen. Große Daten auf separat
  beschreibbarem Datenlaufwerk prüfen, eigene Conda-Umgebung als Alternative.
- Bereiche: eigene neue Remote-Arbeitsordner, neue lokale Werkzeuge/Anleitung,
  AGENTS/HANDOVER und gezielter Zusatz in docs/object_tracking.md.
- Keine Dienstneustarts, keine Änderungen bestehender Conda-Umgebungen,
  keine globalen Python-Pakete, keine Bereinigung fremder Dateien.
- Eigener Arbeitsordner auf RAID1_L angelegt; Python3.11/PyTorch2.5.1+cu121
  installiert. CUDA-Matrixrechnung auf TITAN RTX/Compute7.5 PASS. Offizielle
  Gewichte und Mustard-Demo vollständig geladen, Herkunft/Hashes gespeichert.
- Native Erweiterungen und übrige Vision-Abhängigkeiten installiert; pipcheck PASS.
  Eigener Checkout-Commit a1b694b83e633c2cb6115b9063d940a687759392; minimaler
  lokaler Patch leitet hartcodierten /tmp-Meshexport in privaten TMPDIR um.
- Zwölf-Frame-Demo PASS, danach100Bilder einschließlich tatsächlichem Anheben/
  Drehen in gespeicherter Sequenz PASS. Overlays visuell geprüft. Initialisierung
  zuletzt1,699s, Trackingkern median24,61ms, PyTorch maximal5058MiB reserviert.
  Keine6D-Annotationen im Demoordner; Tiefen-/Maskenfit keine unabhängige Genauigkeit.
- Eigene Jobs beendet; GPU175MiB/0%. Prüfsummen der Systempaketdatenbank,
  vorhandenen Conda-Verläufe und Shell-/Dockerkonfigurationen unverändert.
  Eigener Ordner9,3GiB; Systempartition weiterhin5,5GiB frei.
- Skripte/CLI status|smoke|smoke-motion und Anleitung fertig. Nachweise lokal
  setup/tracking/foundationpose_titanpc_20261113/, Bewegungsdaten in motion/.
- Folgearbeit separat: OAK-Mono-HQ-Tiefe ist noch nicht RGB-ausgerichtet;
  echte UWA-Assets erst mit passender RGB-D-Geometrie/Maske prüfen, anschließend
  Latenz/Frische über WLAN messen. Kein Welt-/Manipulationsnachweis.
