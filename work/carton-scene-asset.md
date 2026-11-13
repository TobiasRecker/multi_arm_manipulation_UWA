# Texturierten Karton als Asset und Zellobjekt übernehmen

- Status: **abgeschlossen**, 2026-11-13, Hauptagent Karton-Asset.
- Nutzerauftrag: rekonstruiertes texturiertes Modell wiederverwendbar ablegen
  und in Gazebo sowie ROS/RViz an der real beobachteten Stelle darstellen.
- Bereiche: description/assets, zentrale Szenenobjekt-Konfiguration,
  Gazebo-/Marker-Anbindung, gezielte Tests und Dokumentation.
- Pose aus T_right_board_object des Bildfits und vorhandener Board-Zellpose;
  keine erneute Kalibrierung oder behauptete vermessene Weltgenauigkeit.
- Neue statische Geometrie zunächst **visual-only**: laufenden Planervergleich
  nicht unbemerkt durch neue Kollisionshindernisse verändern. Keine Armfahrt.
- Bestehende Karton-/Planungsänderungen erhalten. Laufende Sim-Arbeiten vor
  Liveeinfügung prüfen; separater Modellspawn bevorzugt, Zellneustart vermeiden.
- Versioniertes Asset carton_avocado_v1 mit DAE/vierJPEGs, GLB/STL/STEP und
  Hash-/Herkunfts-/Qualitätsmanifest. Zentrale Instanz avocado_carton;
  abgeleiteter unterer Mittelpunkt(-0,013;0,007;0,903)m, +Zoben, visual-only.
- Separates Modell in laufender Gazebo-Zelle erstellt; ursprüngliche Zell-PID
  erhalten, keine Armfahrt/Hardwareaktion. TF/Marker/Gazebo stimmen überein.
  Eigener Asset-Dienst mit Reload und automatischer Einfügung beim Zellstart.
- Beide Pakete gebaut,17gezielte Offlineprüfungen bestanden, inklusive CMake-
  Symlink-Installation. Ein zunächst falscher Pfadgrenzentest korrigiert und
  durch Regressionstest abgesichert; Dateihashes weiterhin zwingend geprüft.
- RViz mit neuem Display geöffnet; direkter Renderexport visuell geprüft,
  Fototexturen/Position bestätigt. Sim-Kamera war durch parallelenReplay nicht
  vorhanden, daher keine Änderung ihrer fremden Einstellungen oder Bildbehauptung.
- Details docs/carton_scene_asset.md; README/AGENTS/HANDOVER aktualisiert.
  Keine offenen Arbeiten für die gewünschte visuelle Einfügung; Kollisions-
  und echte Vermessungsqualität bleiben getrennte spätere Aufgaben.
