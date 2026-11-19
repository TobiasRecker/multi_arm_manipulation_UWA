# CPU- und GPU-Container auf titanpc

- Status in Arbeit, 19.11.2026 (Perth). Nutzer wünscht, längere oder
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
  Beendigung nach sechs Sekunden. GPU-Import und MoveIt-Build laufen.
