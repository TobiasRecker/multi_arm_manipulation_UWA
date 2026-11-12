# Wiederverwendbarer OAK4-Fotodienst

- Status: **abgeschlossen**,2026-11-12, Hauptagent OAK-Foto.
- Auftrag: erprobten Standard/HQ-Fotomodus dauerhaft als Service hinterlegen und
  für spätere Agenten sichtbar dokumentieren.
- Bereiche: oak_camera_calibration/tools/oak4_photo*, eigener Benutzerdienst,
  beide README/AGENTS/HANDOVER und Workspace-AGENTS. Keine Arm-/Kalibrierprofile.
- Geplant: Domain65/LOCALHOST, lazy Kameraöffnung pro Aufruf, ISO100/8Frames/48MP,
  Standard-/Vergleichsaufruf, getrennte SDK-Subprozesse und persistente Metadaten.
- Dienst: nur neuen uwa-oak4-photo.service installieren/starten. Bestehende
  ROS-/SDK-/Simulationsdienste nicht stoppen; exklusiven Zugriff beachten.
- Parallel: shared-view-hardware-captures aktiv; keine UR-Befehle, keine Fahrziele.
- Prüfung: Konfiguration/Fehler/Parallelzugriff, echter Aufruf des installierten
  Dienstes und native Bild-/Metadatenprüfung. Kamera wird danach freigegeben.

- Ergebnis: installiert und aktiviert; echter Vergleich/Metadaten/Parallelzugriff
  bestanden. Sechs isolierte Transaktionstests PASS. AGENTS/README/HANDOVER in
  beiden Repos und Workspace-AGENTS ergänzt. Keine UR-/Simulationsänderungen.

- Finale reguläre HQ-Serviceprobe nach dem letzten Dienstupdate ebenfalls PASS:
  setup/oak4/photos/20261112-140403-hq-f3cec77a/, ISO100, acht unterschiedliche
  native48MP-Frames, exposure_limited=false. Benutzerdienst aktiv und enabled.
