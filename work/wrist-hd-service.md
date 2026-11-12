# HD-Bilddienst für erneute Hardwarekalibrierung

- Status: **in Arbeit**,2026-11-12.
- Nutzer möchte aus dem nachgewiesenen nativen5MP-Aufnahmeweg einen Dienst
  für erneute Kalibrierung. Grünstich allein ist für Grauwert-ChArUco meist
  unkritisch; Schärfe/Kontrast/Clipping und validierter Geometriefit entscheidend.
- Implementierung: gesonderter ROS-Bilddienst/SSH-Aufnahmetransaktion, keine
  Speicherung von Kennwörtern. SSH-ControlMaster/Key-Authentifizierung verwenden.
  Nur Visiondienst kurz freigeben; immer ursprünglichen Normalzustand und alle
  Kameraeinstellungen nachlesen/wiederherstellen, auch bei Fehler/SSH-Verlust.
- Native Bursts und Metadaten für stationäre Aufnahme; zeitliche Messzuordnung
  ohne Belichtungszeitstempel explizit begrenzen. Gleichen Fokus/Bildmodus in
  eigenerHD-Sitzung, bestehendeVGA-Sitzungen/Intrinsics nicht mischen.
- Bereiche: neue wrist_hd*-Module/Remotehelper/C-Quelle/Tests im Controlpaket,
  Paketmanifest/setup.py/Launch; kleine Integration in handeye_hardware.py und
  hardware_sequence.py nach erneutem Difflesen. Parallele linke Vorbereitung
  erhalten; keine realen Fahrziele/Power-/Brake-/Play-Befehle.
- Echte stationäre HD-Serviceprobe ausschließlich right_front; andere Kamera-/
  Treiber-/Simulationsdienste unverändert. Kein Start einer Kalibrierfahrt.
