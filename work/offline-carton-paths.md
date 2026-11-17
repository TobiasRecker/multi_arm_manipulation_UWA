# Schritt 3: feste Eckziele am Avocado-Karton

- Status: abgeschlossen – erste Offline-Einzelbahnstufe, 2026-11-17,
  Hauptagent dieses Chats.
- Auftrag: jeder UR nähert sich seiner nächsten Kartonecke gerade von oben;
  identische feste Zielpose pro Arm über alle IK-Alternativen. Start alle sechs
  Gelenke jedes Arms bei null; diesen Start zuerst im Modell überprüfen.
- Rein offline: primitive Einzelwege/Alternativen und anschauliches Replay.
  Noch keine gemeinsame Zeitkoordination, Kontaktphysik oder Hardwarefahrt.
- Bereiche: neue isolierte Motion-/Tool-Dateien, gezielte Tests, eigener
  Forschungssnapshot/Viewer und Dokumentation. Laufende Karton-/Hardware-
  Arbeiten, bestehende Modelle und Dienste erhalten. Keine Dienstneustarts.
- Nullstart kollidiert (LF-Handgelenk/Greifer gegen rechten Tisch). Nutzer
  ausdrücklich befragt und wählt [0,-90,0,-90,0,0]Grad für alle vier; geprüft.
- Festes Ziel je Ecke, nominaler Greif-TCP145mm über Greiferbasis,15mm unter
  oberer Ecke, diagonale Schließrichtung,120mm senkrechter Anflug. Offene Greifer,
  kein Kontakt-/Tragfähigkeitsnachweis. Kiste lokal als STL-Hindernis aufgenommen.
- Ergebnis:18gültige Endkombinationen,8Einzelbahnen,12kombinierbare Bahnsätze.
  Gemeinsame Startdiagnose423Reserveverletzungen/2.208Samples,0FCL-Kollisionen;
  Zeitkoordination bleibt nächster Schritt. Keine gemeinsame Ausführungsfreigabe.
-88gezielte Pythonfälle/nativer Vorfilter PASS. Unabhängige32.784Einzelzustände
  PASS;20Browserfälle/feste End-TCPs PASS. Viewer Start/Ende visuell geprüft.
- Daten setup/research/offline-carton-paths-20261117/case03/, Anleitung
  docs/offline_carton_paths.md. Fehlenden ersten Modellaufbau/Entwicklungsfall
  erhalten. Keine realen Bewegungen, ROS-Knoten oder Dienstneustarts.
