# Fokus-Schreibtest und Bildfenster für right_rear

- Status: **abgeschlossen**.
- Datum: 2026-11-10, Australia/Perth.
- Nutzer autorisiert begrenzten Fokus-Schreibtest, wünscht Livebild oder Foto
  mit neuem Fokus. Ziel ausschließlich right_rear aus Hardwareinventar.
- Umfang: HTTP-Kameraclient, separates englisches Qt-Fenster mit Fokusregler,
  Snapshot/Restore; vor dem Hardwaretest Einstellungen sichern, Bildvergleich,
  ursprünglichen Fokus/Auto-Modus wiederherstellen. Keine Roboterbewegung,
  Treiber-/Programm-/Power-/Brake-/Adminänderung.
- Bereiche: neue Module/Tests in uwa_cell_control, console entrypoint, eigene
  Anleitung und Handover. Fremde aktive ur-jog-ethernet-GUI-Arbeit erhalten;
  vorhandene GUI/Controller/Simulation nicht neu starten.
- Bild-HTTP-Frische ehrlich anzeigen: Empfang und Bildänderung beobachtbar,
  kein garantierter Sensorbelichtungszeitstempel. Rohbilder/Logs außerhalb Git.
- Ergebnis: Client/Qt-Fenster/ROS-entrypoint und vier lokale HTTP-Tests gebaut.
  Realer manuellerFokus512/Readback/Bildwirkung erfolgreich. Auto-Restore benötigt
  Fokus-Trigger und darf einen neuen Fokuswert bestimmen; Prüfmaßstab korrigiert.
  Echte Qt-Knöpfe/Snapshot/Restore geprüft, andere Kameraeinstellungen erhalten.
  Geprüftes sichtbares Fenster bleibt geöffnet. Bedienung docs/wrist_camera_focus.md;
  Nachweise setup/logs/uwa-wrist-focus-window/ und setup/calibration/wrist_focus/.
  Keine Roboter-/Simulations-/Treiberneustarts. Fremde Jog-Arbeit erhalten.
