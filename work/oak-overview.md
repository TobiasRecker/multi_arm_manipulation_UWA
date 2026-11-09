# Statische OAK4-Übersichtskamera

- Agent/Aufgabe: Codex in OAK-Gespräch, `oak-overview`.
- Status: **abgeschlossen**.
- Aktualisiert: 2026-11-09, Australia/Perth.
- Auftrag: OAK4-D rechts neben den Tischen auf einstellbarem Stativ in Gazebo;
  beide Tische/Roboter überblicken, ChArUco-Details sichtbar halten. Pose noch offen.
- Bereiche: neuer Layoutblock `overview_camera`, neue Kamera-/Stativ-/Analyse-
  Module und Tests, additive Launch-/Setup-Integration; README/AGENTS/HANDOVER.
  Wrist-/Hand-Eye-Implementierung und deren bestehende Diffs bleiben erhalten.
- Parallel zuletzt aktiv: `handeye-diagonal`; keine Simulation neu starten, keine Arme
  bewegen. Kamera als separate statische Gazebo-Entität und eigene TFs hinzufügen;
  Änderungen ihrer Pose dürfen später ohne Zellneustart möglich sein.
- Ergebnis: statische Kamera auf Stativ, zentraler Layoutblock, Livebild und
  CameraInfo/TF/Marker, Auto-Launch, Reload ohne Zellneustart, Projektionsanalyse
  und bildbasierter Boardcheck. 3m/2,6m verglichen, beide Boards erkannt,
  70 Offline-Tests erfolgreich. Nur eigene Kameraentität/Dienste gesteuert.
- Belege/Bedienung nach `docs/oak_overview.md`, README und HANDOVER übertragen.
  RGB-Livefenster der Simulation bleibt offen, Endpose3m; physische OAK unberührt.
- Grenzen: nominelle Optik/Extrinsics; Stativ nur visuell, nicht in MoveIt.
  Bestehender Zelllaunch nicht für diese Aufgabe neu gestartet, sondern Kamera
  zur laufenden Welt hinzugefügt. Keine weitere Zell-/Armprüfung geplant.
