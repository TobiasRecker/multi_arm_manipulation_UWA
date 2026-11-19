# CPU- und GPU-Container auf titanpc

- Status in Arbeit, 19.11.2026 (Perth). Nutzer wünscht, längere oder
  rechenintensive CPU- und insbesondere GPU-Jobs bevorzugt auf titanpc
  in Containern auszuführen. Betroffen sind Workspace-/Zellregeln, ein
  eigener Compute-Ordner auf titanpc und Start-/Abrufwerkzeuge. Keine
  geplanten Neustarts. Die parallele reale Zellarbeit läuft separat.
- Lesend bestätigt: 7800X3D mit 8 Kernen/16 Threads, 30 GiB RAM, TITAN RTX
  mit 24 GiB, 6 GiB auf Root und rund 516 GiB auf RAID1_L frei. Benutzer-
  Namespaces, FUSE-Gerät und bestehender systemd-Benutzermanager verfügbar.
