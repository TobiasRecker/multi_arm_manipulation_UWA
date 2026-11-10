# Erster Wrist-Camera-/Hand-Auge-Test an right_rear

- Agent/Aufgabe: Codex, `right-rear-wrist-hardware`.
- Status: **abgeschlossen**.
- Aktualisiert: 2026-11-10, Australia/Perth.
- Nutzerziel: erste reale Tests zunächst ausschließlich hinten rechts,
  `right_rear` / 192.168.8.170; Kamerabild abrufen und Vorgehen klären.
- Umfang jetzt: Herstellerquellen, bestehende Anbindung, lesender HTTP-Bildabruf
  und Dashboard-Status; konkrete Anleitung. Keine Roboterbewegung, Treiberstarts,
  Power-/Brake-/Programm-/Remote-Änderungen oder Kamera-Konfigurationsänderungen.
- Bereiche: eigene Anleitung, kleine README-/HANDOVER-Ergänzungen, lokale
  Diagnoseartefakte unter `setup/logs/right-rear-wrist-2026-11-10/`.
- Parallel aktive Aufgabe `uwa-ur-gui`: deren Code/Diffs erhalten; keine
  Dienstneustarts oder gemeinsamen Tests.
- Ergebnis: Hersteller-URL und USB-Alternative geprüft; konkrete Anleitung
  `docs/right_rear_hardware_first_test.md`, README/AGENTS/HANDOVER aktualisiert.
  HTTP aktuell `No route to host`, Dashboard Timeout; WLAN-Route vorhanden.
  Kein Bild empfangen, Ursache offen; keine Hardwarezustände geändert.
- Empfohlener nächster Umsetzungsschritt: Hardware-Recorder für manuell am
  Pendant angefahrene Stellungen, reale Intrinsics/UR-Kinematik und gesicherte
  Bildfrische prüfen. Noch kein Hardware-Recorder oder automatischer Lauf erstellt.
