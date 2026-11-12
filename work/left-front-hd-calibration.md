# Native HD-Kalibrierung vorne links

- Status: **in Arbeit**, 2026-11-12, Hauptagent LF-HD.
- Nutzer beauftragt nach bestandener VGA-Kalibrierung getrennte native HD-Reihe.
- Erst Kamera-only: CB3 i686/Linux3.14/Python2.7 ohne gcc; nativen V4L2-Helfer
  prüfen, bestehende Sicherung/Rückstellung beibehalten. UCC1.11.1, Kamera
  028E1F350009061C, VGA-Fokus245 manuell unverändert sichern.
- Andere Aufgaben right-rear-hd-intrinsics und Karton-Rekonstruktion erhalten;
  keine fremden Dienste, Treiber oder Kameratransaktionen berühren.
- Neue Daten unter setup/calibration/hardware_handeye/left_front_hd_20261112/.
  Kein Mischen mit VGA, kein automatisches Aktivieren. Neue Bewegungswege nur
  nach vollständiger Prüfung und konkreter Freigabe.
