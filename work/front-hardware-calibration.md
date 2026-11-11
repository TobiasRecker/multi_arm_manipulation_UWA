# Front-Kalibrierung mit größerer, räumlich vielfältigerer Reihe

- Status: **62-Bilder-Versuch und Vergleich abgeschlossen; Hand-Auge-Profil nicht freigegeben**.
- Abschluss:2026-11-11, Australia/Perth. Hauptaufgabe.
- Nutzer akzeptiert Rear-Parken und62 Frontbilder (50 Fit/12 reservierte Prüfung)
  sowie anschließenden20/33/50-Fit-Teilmengenvergleich bei gleichem Prüfsatz.
  Je konkrete Rear-Park-/Front-Gesamtvorschau und freier Fahrraum bestätigt.
- Rear-Parkfahrt SUCCEEDED/0,56,5s,0,0000296rad Endfehler. Front-Erstansicht
  SUCCEEDED/0,78,9s,0,0000318rad Endfehler, reales Board24 Ecken.
- Front nach Benutzer-URCap-/USB-Recovery erreichbar. Autofokustrigger hatte
  HTTP-Reset; danach scharfen435-Fokus manuell fixiert und per mehreren
  Hardware-Readbacks/frischen Bildern bestätigt.60000µsManual/Gain16.
- Ganze62-Reihe aufgenommen,14…24 Ecken und individuelle Payloads.12-Prüfrollen
  nie zum Fit verwendet. Nur ein Arm gleichzeitig, Originalziele/Rollen bei
  jeder Wiederaufnahme erhalten, neue aktuelle Verbindungswege komplett geprüft.
-043 wegen Kabelverdeckung9 Ecken abgelehnt, Front deaktiviert. Nutzer sichert
  Kabel ohne Kamera-/Boardverschiebung. Abgelehnten Versuch mit SHA256 unter
  rejected/sample_043_attempt_01/ aufbewahrt,043 stationär mit24 Ecken wiederholt.
  Neun gemeinsame Ecken vor/nach Sicherung Median0,025px/Maximum0,063px versetzt.
-060 nativer C153A5/Wrist3: Nutzer bestätigt Kabelspannung, löst sie. Pending-
  Action gecancelt/Front inaktiv, kein automatischer Reset. Nach NORMAL/PLAYING
  aktuelle Winkel neu gelesen, Kamera von424Auto auf435Manual zurückgesetzt
  und Hardware-Readback geprüft. Originale060/061 neu geprüft/ausgeführt.
- Intrinsics PASS: Fit0,289px, Median Prüfung0,299px. Hand-Auge FAIL:
  Median Reprojektion0,748px, Boardposition2,344mm, Rotation0,652° >0,5°.
  Keine Gütegrenze gesenkt, keine Ausreißer ausgeschlossen, nichts aktiviert.
 60er-Zwischenergebnis49Fit/11Prüfung separat in analysis_60_views/ erhalten.
- Bildzahlvergleich:20Fit/33Fit je4 feste verschachtelte Auswahlen,50Fit einmal;
  dieselben12 Prüfbilder. Rotations-RMS0,623…0,775° /0,607…0,745° /0,652°.
  Kein klarer großer Bildzahlgewinn, alle Varianten verfehlen Rotationsgrenze.
- Daten setup/calibration/hardware_handeye/right_front_20261111/; versionierte
  negative Bewertung evaluation_v1/ samt SHA256/Prüfgrafiken/Tabellen. Berichte
  docs/front_calibration_2026-11-11.md und HANDOVER.md aktualisiert.
- Software: optionale Wide-Planung, Hardware bis80 Bilder, ursprüngliche
  Standard-/Simulationsplanung erhalten; Offline-count_comparison ohne
  Profiländerung. Tatsächliches natives SafetyMode cancelt nun wartende
  Actions auch bei Programmlinktrue. Keine neuen manuellen GUI-Freigabegates.
-22 abschließende gezielte Tests bestanden, zuvor3 Vierarm-/Fit-/Holdout-
  Regressionen. Offline-Vergleich reproduziert9 alte Rear-Teilmengen exakt;
  altes Rear-Profil SHA256-unverändert.
- Endzustand: beide URs NORMAL/PLAYING, skalierte JTC halten Rear-Parkpose und
  Front-Letztpose. Frontendfehler0,0000460rad, Rear-Endvergleich0,0000858rad.
  Eigene Vorschauen beendet, Hardware-GUI/Treiber offen, keine weiteren Ziele.
- Front-Dashboardversion5.26.3.140631 erst nach allen Fahrten im Inventar
  nachgeführt. Gespeicherte alte Planfingerprints dadurch zusätzlich veraltet.
- Nächster fachlicher Schritt: Rotationsinkonsistenz gezielt diagnostizieren;
  keine absolute Genauigkeitszusage oder Aktivierung des fehlgeschlagenen Profils.
