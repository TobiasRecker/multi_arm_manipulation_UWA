# Reale Übernahme Motion review,19.11.2026

- Status: aktiv, Hauptagent des realen Kartongreifchats. Nutzer verlangt neuen
  Kartonablauf ausdrücklich über UWA Robot Power → Motion review. Bestehende
  Hardwarepause endet für Vorbereitung/Review; reale Ziele nur über GUI-Ticket.
- Vier URs bei reinem Lesetest POWER_OFF/runtime1/safety1, alle q-Spannen0.
  RF/LF strenge stationarity_observed flagsFalse im ausgeschalteten Modus;
  diese Daten nicht als aktuellen gültigen Home-Fahrstart übernehmen.
  Rechte Greifer offen OBJ3/POS3. Neue Motion-Review-Runtime bisher inaktiv.
- Geplant: eigene N100-Dienste geordnet stoppen (keine Power/Brake-Befehle),
  aktuellen geprüften Pilotstand stagen/bauen, Betriebsanbindung mit identischem
  Trendprofil bereitstellen. Bereichsfreigabe und Vertrauen nur vom Nutzer
  in GUI; kein automatisches Bestätigen von Bedienentscheidungen.
- Neue Aufnahme nach tatsächlicher Bereichsfreigabe, passende ROI/validierte
  Kamerareferenz und --planar-texture; aktuelle Startmessung und komplette
  Anfahrt/Einfahrt als eine Reviewrevision. Kontaktreview nach tatsächlichem
  Einfahrbild. Bestehende vorbereitete Pose/Pläne nur Referenz, kein Blindstart.
- Daten setup/tasks/carton_motion_review_20261119/ auf ROSmini und N100.
  Hardwarezugriffe ausschließlich durch diesen Auftrag; keine Fremddienste.
