# CPU- und GPU-Container auf titanpc

- Status abgeschlossen, 19.11.2026 (Perth), Hauptagent dieser Einrichtung.
  Nutzer wünscht, längere oder
  rechenintensive CPU- und insbesondere GPU-Jobs bevorzugt auf titanpc
  in Containern auszuführen. Betroffen sind Workspace-/Zellregeln, ein
  eigener Compute-Ordner auf titanpc und Start-/Abrufwerkzeuge. Keine
  geplanten Neustarts. Die parallele reale Zellarbeit läuft separat.
- Lesend bestätigt: 7800X3D mit 8 Kernen/16 Threads, 30 GiB RAM, TITAN RTX
  mit 24 GiB, 6 GiB auf Root und rund 516 GiB auf RAID1_L frei. Benutzer-
  Namespaces, FUSE-Gerät und bestehender systemd-Benutzermanager verfügbar.
- Rootloses Apptainer 1.5.5-1 im eigenen RAID1_L-Verzeichnis installiert.
  Das Debian-Paket brauchte eine auf dem Host fehlende Bibliothek. Die
  offizielle relocatable RPM-Variante mit BusyBox-Stdin-Adapter funktioniert.
  Der CPU-Job mit Ubuntu 26.04/Lyrical hat schreibgeschützte Eingaben,
  getrennte Ausgaben und fehlende Netzwerkroute bestätigt. Ablauf über
  die bestehende Benutzer-Unit, Abschluss nach SSH-Ende und Ergebnisabruf
  geprüft. Ein eigener Testjob bestätigt wirksame CPU-/RAM-Grenzen und
  Beendigung nach sechs Sekunden. Gezielter Abbruch und unveränderte
  Übergabe von Argumenten mit Leerzeichen und Dollarzeichen geprüft.
- GPU-Image importiert, `torch 2.7.1+cu126` rechnet eine Matrix erfolgreich
  auf der TITAN RTX (CUDA 12.6, Compute Capability 7.5). Planungsimage mit
  root-gemapptem Namespace (`--ignore-subuid`) gebaut, da die Host-Binaries
  `newuidmap`/`newgidmap` fehlen. Build-Budget für den eigenen laufenden
  Dienst verlängert und temporäre Einstellung nach Abschluss entfernt.
  MoveIt-FCL erkennt einen echten synthetischen Kollisionsfall und den
  freien Kontrollfall im planungsspezifischen Job. SciPy-Probe bestanden.
- Fertige Images und SHA-256 unter `uwa-compute/images/` auf RAID1_L.
  Eigene Build-/Prüfdienste beendet. Host-, Ablauf- und Ergebnisnachweise
  unter `setup/titanpc/results/`. Hauptanleitung `setup/titanpc/README.md`.
