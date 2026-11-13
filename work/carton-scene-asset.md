# Texturierten Karton als Asset und Zellobjekt übernehmen

- Status: **in Arbeit**, 2026-11-13, Hauptagent Karton-Asset.
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
