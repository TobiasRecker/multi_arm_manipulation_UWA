# Kameraskript und Controller-Dateizugriff

- Status: **abgeschlossen** (Erklärung und Zugriffsprüfung).
- Datum: 2026-11-10, Australia/Perth.
- Nutzer fragt nach erzeugter `.script`-Datei und Übernahme der lesenden
  Controller-/URCap-Untersuchung durch Codex, gegebenenfalls Zugangsdaten.
- Umfang: offizielle Dateipfade/URScript-Erklärung, bestehende schlüsselbasierte
  SSH-Verbindung prüfen; nach Ablehnung vorhandener Schlüssel einmalig den
  öffentlich vom Hersteller dokumentierten Standardzugang prüfen, keine
  weiteren Passwortvarianten. Keine Programme ausführen,
  keine Controllerdateien/Einstellungen ändern. Diagnose nur right_rear.
- Bereiche: eigene Statusdatei, Hardware-Testanleitung/HANDOVER.
  Parallele aktive `ur-jog-ethernet`-Arbeit erhalten; keine Dienstneustarts.
- Ergebnis: offizieller Programme-Pfad/URScript-Dateityp bestätigt. SSH erreichbar,
  vorhandene Standardschlüssel und ein dokumentierter Standardlogin abgewiesen.
  Keine Controllerdateien gelesen oder Befehle ausgeführt. Weitere Untersuchung
  wartet auf funktionierenden Zugang oder lokal bereitgestellte Dateien.
- Folgefrage: Nutzer möchte ein temporäres Kennwort einrichten. Offizielle
  PolyScope-ab5.10-Anleitung für Password/Admin und SSH-Authentifizierung geprüft;
  aktuelles Admin-Kennwort für Änderung nötig. Keine Passwortänderung ausgeführt,
  kein neues Kennwort empfangen/gespeichert. Schlüsselimport bleibt Alternative.
