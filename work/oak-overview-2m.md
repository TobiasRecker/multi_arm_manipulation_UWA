# OAK-Übersicht mit maximal 2 m Stativhöhe

- Agent/Aufgabe: Codex OAK-Gespräch, `oak-overview-2m`.
- Status: **abgeschlossen**.
- Aktualisiert: 2026-11-09, Australia/Perth.
- Nutzerkorrektur: Stativ erreicht höchstens 2 m. Geeignete Übersichtspose suchen,
  beide Tischplatten und ausreichend ChArUco-Details erhalten.
- Ergänzende Nutzerangabe: zwei OAK-D-S2-FF sind als mögliche Zusatzkameras für
  tote Winkel vorhanden. Keine festen Posen / keine Hardwareanbindung beauftragt.
- Bereiche: ausschließlich Übersichtskamera-Layout, zugehörige Pose-Annahmen
  in Tests/README/Anleitung/AGENTS/HANDOVER. Kalibrier-/Roboteränderungen erhalten.
- Parallele Aufgabe `handeye-diagonal`: keine Arme bewegen, keine Zell-/Scan-
  Neustarts. Nur eigene Kamera über Layoutparameter und Reload umsetzen.
- Ergebnis: zentrale Pose[1.8,-0.8,2.0]m / Ziel[0,-0.1,.95]m,4000×3000@3Hz,
  rund28,5° nach unten. Alle acht Tisch-Ecken geometrisch und vier Arme/Tische
  im geprüften Bild sichtbar.12/24 ChArUco-Ecken links/rechts, RMS0,691/0,042px.
  Links wenig Detailreserve; keine Zusicherung für alle bewegten Armstellungen.
- Kandidaten: mittig rechts schwache linke Erkennung, starke Diagonalen durch
  Arme verdeckt, seitlich versetzte4k-Posen brauchbar.6k lieferte kein erfolgreich
  empfangenes RGB,5k ebenfalls nicht durchgängig erfolgreich; kein Hardwarelimit
  daraus behauptet. Stabiles4k-Profil wiederhergestellt; nur Kamera umgesetzt.
- Aktiver Layoutpfad wieder zentrale Quelldatei; keine temporäre Variantendatei.
  13 Tests bestanden, README/Anleitung/AGENTS/HANDOVER in beiden Repos aktualisiert.
  Belege `setup/logs/uwa-oak-2m/`, Zusammenfassung in
  `docs/oak_overview_2m_validation_2026-11-09.json`.
