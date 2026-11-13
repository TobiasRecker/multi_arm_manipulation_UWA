# Statische 6D-Posenbestimmung und dynamisches Objekttracking

- Status: **in Arbeit – Architektur und erster Offline-Prototyp**, 2026-11-13.
- Nutzerziel: bekannte digitalisierte Assets wiederfinden; statisch vor
  Greifen/Manipulation möglichst genaue Pose, dynamisch schnelle Onlinepose.
- Zuerst gespeicherte Bilder/Asset verwenden; keine Armfahrt, keine Wiederaufnahme
  der pausierten Planungsvergleiche, keine ungefragten Kamera-/Dienstwechsel.
- Hardware: lokal Intel-Arrow-Lake-Grafik, keine erkannte NVIDIA-GPU. Optionale
  Nutzerfrage nach weiterem GPU-Rechner offen. FoundationPose/M3T-Quellen prüfen.
- Gemeinsame Objekt-ID und unveränderter Assetframe; keine bekannte simulierte
  Objektpose als Schätz-Start oder Ergebnis unterschieben. Erst Kamerapose des
  Objekts; Weltpose nur mit zeitlich passender, gekennzeichneter Registrierung.
- Datenqualität/Verdeckung/Mehrdeutigkeit, Bildalter und LOST explizit ausgeben.
  Modellfehler und vorläufige Kamerakalibrierung begrenzen reale Genauigkeit.
- Geplante erste Bereiche: eigenständiger Trackingkern, assetgebundene
  Oberflächenmerkmale, offline statische Initialisierung und schnelle zeitliche
  Verfolgung mit Wiedererkennung; getrennte statische/dynamische Prüfung.
