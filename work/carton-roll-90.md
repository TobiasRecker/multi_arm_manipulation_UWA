# Karton um Längsachse drehen

- Status: in Arbeit, 2026-11-16 (Australia/Perth), Codex dieser Sitzung.
- Auftrag: vorhandene Zweiarm-Kontaktpipeline wiederverwenden; Karton 90° um
  Längsachse drehen, Öffnung zur Kamera, in Seitenlage auf Tisch abstellen.
- Annahme: Kamera = feste OAK-Übersicht; Drehrichtung aus deren Weltpose.
- Bereiche: uwa_cell_tasks Planung/Runtime/Profil/Prüfung, Dokumentation.
- Erst vollständigen geometrischen Zeugen einschließlich Drehung/Absetzen
  vor Greifbewegung prüfen. Bestehende Guard-/Kontakt-/Stopppfade erhalten.
- Keine Hardwareaktionen, keine fremden Dienste neu starten. Eigene neue
  immutable Szene für spätere Kontaktprüfung; frühere Quellenbindungen erhalten.

## Parallelbetrieb / Versionskonflikt

- Host-Prozessprüfung erfordert unsandboxed lesendes `ps`; sandboxed `ps`
  zeigt die anderen Greifprozesse nicht. Prüfung leider erst nach ersten
  Quelländerungen erfolgt. Fremde Reihe `carton_preload_faults_20261116_02`
  hatte case01 aktiv; dessen Versionsprüfung stoppte in review_strategy:
  `Task implementation changed; prepare and relaunch the scene`.
  Beide Holds bestätigt; kein Öffnen beauftragt. Nicht als Fault-PASS zählen.
- Keine fremden Prozesse beendet; keine zweite Greifwelt gestartet. Geänderte
  Pythonquellen werden in bestehenden Szenen korrekt als ungültig erkannt.
- Offline-Erstprüfung in setup/tasks/carton_roll_20261116_01; diese enthält
  einen zwischenzeitlichen Quellstand und ist Entwicklungs-, kein Livebeleg.

## Geometrische Entwicklung

- 216 sichtbare Markdown-Dateien/24614Zeilen systematisch inventarisiert und
  nach Manipulations-/Kartonbezügen durchsucht; Arbeitsregeln, Übergaben,
  Skill und zentrale Pipeline-/Asset-Anleitungen vertieft gelesen.
  Inventar mit Hashes: setup/tasks/carton_roll_20261116_01/markdown-inventory.json.
- Nominell146mm Hub nötig, Drehung+90° um Asset-X am Materialschwerpunkt.
  Öffnungsnormalen-/Kamerakosinus0,805. Rechter minimaler Absetzpunkt scheitert
  im ersten Absenkabschnitt an RF-Unterarm/Wrist3-Selbstkollision. Alle10
  Originalgriffe geprüft; andere scheitern auch an Geometrie/IK/Reserve.
-48Startzweige,30rechteAbsetzvarianten und30Greifer-Headingvarianten ohne
  vollständigen Grobpfad. Keine Unmöglichkeitsaussage für alle denkbaren Bahnen.
  Testvarianten nicht in die produktive Griffstrategie übernommen.
- Linke Absetzalternative:41Samples proPhase grob FCL-/IK-frei. Bei0,05rad/s
  Armgrenze fehlt am Ende bis1,669mm RR/RF-Stoppreserve. Separater gemeinsamer
  Hüllcheck derselben123Zustände:0,045→14,306mm;0,04→24,739mm Mindestreserve.
  Profil daher konservativer0,04rad/s, alle Abstandsschwellen unverändert.
- Vollständige räumliche Bahnscreens für alle Phasen vor teurer Zeitparametrierung;
  danach vollständige dichte Interpolationsprüfung unverändert. Kein Ersatz
  der Endprüfung durch Grobsamples. Runtime/CLI prüfen ganzes Rezept vor Einfahrt;
  nach Kontakt mit eingefrorenen gemessenen Offsets vor Lastübernahme erneut.
- Szene01 explorativ / Zwischenquellen, Szene02 verworfene0,05rad/s-Variante,
  Szene03 aktueller0,04rad/s-Dichtprüflauf. Keine als Kontakt-PASS ausgeben.
