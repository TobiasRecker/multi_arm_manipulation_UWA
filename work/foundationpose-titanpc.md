# FoundationPose auf gemeinsamer NVIDIA-Workstation

- Status: **in Arbeit**, 2026-11-13, Hauptagent dieses Gesprächs.
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
- Nächster Nachweis: CUDA-Smoke-Test, native Erweiterungen, Gewichte und
  offizielle RGB-D-Demo. OAK-Mono-HQ-Tiefe ist noch nicht RGB-ausgerichtet;
  echte UWA-Posen erst mit passender RGB-D-Geometrie gesondert prüfen.
