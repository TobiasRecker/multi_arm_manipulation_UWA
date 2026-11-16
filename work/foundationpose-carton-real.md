# Erster FoundationPose-Funktionstest mit realem Karton

- Status: **abgeschlossen – erster statischer Realtest visuell plausibel**,
  2026-11-16 (Australia/Perth), Hauptagent.
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
- Aufnahme setup/oak4/rgbd/20261116-111619-rgbd-5a8d0ae9/, sichtbare Startkontur
  manuell annotiert. Modell292Dreiecke, UV-Atlas/OBJ-Rückimport/Metereinheit und
  Unabhängigkeit vom gespeicherten Szenenposefeld geprüft.
-1280×960 erreicht45%-Allocatorlimit. Unverändertes Limit, neue Arbeitskopie
 640×480 mit korrektem Pixelzentrum-K und nearest-Tiefe/Maske; Originale erhalten.
- AchtFrames PASS:1,623s Registrierung,18,806ms mediane Kernzeit,6,55s Gesamt;
  maxPyTorch5068MiB reserviert. Box und Texturrückrender visuell plausibel.
  IoU0,913/Tiefenrest7,08mm sind Eingabekonsistenz, keine Genauigkeit.
- Eigene Jobs beendet, GPU175MiB/0%, heutige Workstation-Hashes unverändert,
  Kamera-Lease frei.38OAK-Tests/9Subtests und3Exporttests bestanden.
- Nachweise setup/tracking/foundationpose_carton_20261116/, Anleitung und
  Übergaben gepflegt. Offen als Folgearbeit: echte Bewegung/Verdeckung,
  Wiederfinden, WLAN-Livepfad und unabhängige metrische Prüfung; keine
  Manipulationsfreigabe oder globale ROS-/Kalibrieraktivierung.
