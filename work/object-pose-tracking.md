# Statische 6D-Posenbestimmung und dynamisches Objekttracking

- Status: **in Arbeit – Architektur und erster Offline-Prototyp**, 2026-11-13.
- Nutzerziel: bekannte digitalisierte Assets wiederfinden; statisch vor
  Greifen/Manipulation möglichst genaue Pose, dynamisch schnelle Onlinepose.
- Zuerst gespeicherte Bilder/Asset verwenden; keine Armfahrt, keine Wiederaufnahme
  der pausierten Planungsvergleiche, keine ungefragten Kamera-/Dienstwechsel.
- Hardware: lokal Intel-Arrow-Lake-Grafik, keine erkannte NVIDIA-GPU. Nutzer
  bestätigt: zunächst Mini-PC, NVIDIA-Rechner möglicherweise später verfügbar;
  Beschaffung von Compute parallel durch ihn. Backendtausch offen halten.
- Gemeinsame Objekt-ID und unveränderter Assetframe; keine bekannte simulierte
  Objektpose als Schätz-Start oder Ergebnis unterschieben. Erst Kamerapose des
  Objekts; Weltpose nur mit zeitlich passender, gekennzeichneter Registrierung.
- Datenqualität/Verdeckung/Mehrdeutigkeit, Bildalter und LOST explizit ausgeben.
  Modellfehler und vorläufige Kamerakalibrierung begrenzen reale Genauigkeit.
- Geplante erste Bereiche: eigenständiger Trackingkern, assetgebundene
  Oberflächenmerkmale, offline statische Initialisierung und schnelle zeitliche
  Verfolgung mit Wiedererkennung; getrennte statische/dynamische Prüfung.
- Neues Paket uwa_cell_tracking gebaut: Textur-SIFT/3D-PnP-Initialisierung,
  statischer3-Frame-Burst, LK/PnP-Tracking, ROS-Pose/Status/Overlay mit Worker,
  explizites Start/Stop/Localize und Zeit-/Frische-/Kalibrierprüfungen.
- Offline6Tests und isolierter ROS-Replay Domain71 bestanden. Statische OAK-
  Auswertung1,4s; dynamische Kerne10msWrist/46msOAK, keine behauptetenLiveFPS.
  LF nicht verwendet; LR/RF bleiben teilsLOST/AMBIGUOUS, nichtzwangslokalisiert.
- Nächste Prüfung: opt-in OAK-Stream Domain65, bestehender SDK-Worker erhält
  zusätzliche Tracking-Metadaten/K/D und parametrisierte10fps/1600×1200;
  bestehende2fps/2000×1500-Vorschau unverändert. Gemeinsame Foto-Lease erhalten,
  keine fremden Kameranutzer stoppen oder Kamera automatisch resetten.
