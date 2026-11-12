# Kalibrierung links hinten vorbereiten

- Status: **Software/Entwurf vorbereitet; aktive URCap-Konfiguration und rechte Hindernisstellungen offen**,2026-11-12, Hauptagent.
- Nutzer hat left_rear eingerichtet; Auftrag: Erreichbarkeit prüfen und
  Kalibrierung vorbereiten. Keine neue reale Fahrfreigabe ableiten.
- Ziel192.168.8.169, External Control PC192.168.8.209/Port52002, Domain66.
  Bestehende drei Treiber und andere Aufgaben erhalten; keine pauschalen Kills.
- Bereiche: rein lesende Dashboard-/Kamera-/ROS-Diagnose, Linksarm-Fähigkeit
  des Hardware-Kalibrierwerkzeugs, getrennte Sitzungs-/Planartefakte und
  Bedienung/HANDOVER. Bisherige Kalibrierprofile erhalten.
- Prüfen: aktuelles Board/Format, Kamera/Fokus/Bildmodus, alle Armzustände,
  Kinematik/FK, vollständige MoveIt-Szene, ausführbare oder ausdrücklich
  unbestätigte Vorschau. Keine Power/Brake/Play/Controlleraktivierung/Fahrt.
- Folgeanweisung: Nutzer beauftragt ausdrücklich Einschalten/Bremsenlösen/
  Programmstart über vorhandenen MATCH-Ablauf; deshalb diese früher ausgeschlossenen
  Vorbereitungsschritte nun ausgeführt. Keine Freigabe für Fahrziele.
- left_rear erreichbar, RUNNING/NORMAL/Remote nach MATCH-Prepare, ros.urp
  nativ geladen/PLAYING mit tobias.installation. External-Control-Link bleibt
  false, keine Verbindung an52001–52004 trotz passender Listener undPC209.
  Nutzer um aktive URCap-/Programmknotenprüfung Host209/Port52002 gebeten.
- Hinten rechts Local/POWER_OFF liefert Nullwinkel; gültige aktuelle rechte
  Hindernisstellungen noch offen. Nutzer um Remote/Einschalten dort gebeten.
  Bestätigt: linkes40mm-A3-Tischboard und links vorne aufrechtes Home unverändert.
- Hardware-CLI auf alle vier Arm-IDs erweitert;25 Offline-Tests inkl. echter
  MoveIt-/IK-Sweeps rechts/links, CLI-Auswahl und zwei Lyrical-Startup-Warnpfaden.
  MATCH ur_startup_enable.py .warn→.warning repariert. Build UWA-Control erfolgt.
- Reine Entwurfsvorschau34,1s unter setup/calibration/hardware_handeye/
  left_rear_20261112/design_preview/, ausführbar=false, rechte Arme unbestätigt.
  Ablauf41 Gesamtbilder(33Fit/8Prüfung)/wide vorbereitet, noch keine Sitzung
  begonnen. Kamera640×480/3verschiedeneFrames,439Auto nur gelesen, kein Board
  im aktuellen Bild. Fokus/Boardbild nach erster freigegebener Pose prüfen.
- Daten/Diagnose unter .../preparation/, insbesondere preparation-plan.json und
  final-readiness.json. docs/left_rear_calibration_preparation_2026-11-12.md,
  README/AGENTS/HANDOVER aktualisiert. Keine Fahrziele/Schutzquittierung;
  alte Besitzer-GUIs/drei Treiber erhalten. Eigenes zusätzliches Beobachterfenster
  ohne Treiberbesitz beendet. Nach Klärung frische vollständige Planung, konkrete
  Vorschau und Fahrfreigabe erforderlich; Entwurf nicht einfach ausführen.
- Letzter Snapshot während der erbetenen Pendantprüfung: left_rear RUNNING/
  Local/STOPPED ros.urp, beide rechten POWER_OFF/Local. Keine erneuten
  Programmstartversuche, solange der Nutzer die aktive Konfiguration prüft.
