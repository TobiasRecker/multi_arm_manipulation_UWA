# HD-Bilddienst für erneute Hardwarekalibrierung

- Status: **abgeschlossen – Dienst und Kalibrieradapter real geprüft**,2026-11-12.
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
  Paketmanifest/setup.py; kleine Integration in handeye_hardware.py und
  hardware_sequence.py nach erneutem Difflesen. Parallele linke Vorbereitung
  erhalten; keine realen Fahrziele/Power-/Brake-/Play-Befehle.
- Echte stationäre HD-Serviceprobe ausschließlich right_front; andere Kamera-/
  Treiber-/Simulationsdienste unverändert. Kein Start einer Kalibrierfahrt.

- Ergebnis: ROSCapture/Status/CompressedImage fürright_front implementiert,
  drei native5MP-Frames pro Aufruf,konkurrierende Anfragen gesperrt. SSH nur
  interaktiver ControlMaster/Key,nativeSource in separaterHD-Sitzung gespeichert.
- Kalibrieradapter spinnt beimWarten weiter,verwirft transiente Bewegungs- und
  Guardfehler erst nach Restore,schützt HD/VGA-/Kamera-ID-Trennung undfitten
  neueHD-Intrinsics. Kein realer Kalibrier-/Bewegungsauftrag gestartet.
- Native Webcamquelle über tatsächlichen runit-CWD identifiziert. Erstes
  Discoveryproblem sicher vor Zustandsänderung abgewiesen und korrigiert.
  RemoteRestore wartetNormal,beachtet tatsächlicheSetterwirkung undprüft alle
  Originalwerte; Watchdog/Freigabe-Retry/diagnostische Dateien implementiert.
- Reale Service-/Clientprobe3×2592×1944,je24Ecken,16,04s,502Monitorhooks,
  max32,8msAbstand; Statusbeantwortung/Busy-Ablehnung undRestore vollständig
  geprüft. Keine reale Bewegungs-/Stoppprobe,nur stationäreKameraerprobung.
-29 Offline-Tests/Paketbuild bestanden. Logs setup/logs/uwa-wrist-hd-*.log,
  Service weiteroffen; alte Dateien/Profile/andereArmprozesse erhalten.
  HANDOVER/README/AGENTS unddocs/wrist_hd_service.md aktualisiert.
