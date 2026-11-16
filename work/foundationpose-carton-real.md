# Erster FoundationPose-Funktionstest mit realem Karton

- Status: **in Arbeit**, 2026-11-16 (Australia/Perth), Hauptagent.
- Nutzer bietet bekannten Avocado-Karton an und bestätigt Sichtbarkeit/Ruhe.
  Kamera-only-Aufnahme, danach offline GPU-Test, keine Arm-/Programmaktion.
- Bereiche: eigene Export-/Eingabewerkzeuge, vorhandener GPU-Testpfad,
  neue Artefakte unter setup/tracking und dem eigenen Remote-Arbeitsordner.
  Bestehende Asset-/Kalibrier-/Welt-/ROS-Profile unverändert lassen.
- Bekannte Grenzen: RGB-D-Referenzabweichung ansichtsabhängig, mobiles Board
  fünf Felder lautLineal191 statt190mm. Keine Präzisions-/Manipulationsfreigabe.
- Meshframe/Metereinheit und Texturen erhalten. Gespeicherte Szenen-/Boardpose
  des Assets niemals als Initialisierung verwenden. Initialmaske explizit
  als eigene sichtbare Bildannotation mit Unsicherheit kennzeichnen.
- GPU-Workstation derzeit erreichbar/frei; eigener bestehender Python-Prefix,
  kein Installieren globaler Pakete oder Ändern bestehender Nutzerumgebungen.
