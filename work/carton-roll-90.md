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

## Erster vollständiger geometrischer Nachweis

- Szene03/PASS wall_0_0.5: beide rechten Arme,146mmHub,90°Drehung, linker Tisch.
  Dichte FCL-/IK-/starreKorridor-/Geschwindigkeits-/Beschleunigungs-/Ruckprüfung
  bestanden. Anfahrt und Einfahrt separat PASS; Einfahrendzustand und direkter
  Start des Trageplans unterscheiden sich maximal3,1e-12rad. Kein Kontaktlauf.
- Alte globale Gradient-/Krümmungsschranke erzeugt1588,6s Drehzeit trotz sehr
  niedriger tatsächlicher Befehlsableitungen. Quelle03 vor Änderung in
  implementation_snapshot/{planning,timing}.py erhalten; Szene03 bleibt Beleg
  dieses älteren langsameren Stands, nicht aktuelle Quellenbindung.
- Neues nur fürs Drehrezept genutztes analytisch konservatives Intervall-Timing:
  jedes CubicSpline-Stück mit exakt zugehörigem Quintik-Zeitintervall koppeln;
  Ableitungsextrema einschließlich innerer Extrema verwenden. Kein unabhängig
  retimter Arm, keine gelockerten Limits. Gegenprobe mit200001Zeitpunkten und
  hoher Endpunktkrümmung PASS.44Pythonfälle und8CTest-Suites PASS.
- Neue Szene04 prüft verbesserten Stand vollständig; bisherigen Beleg nicht
  umetikettieren. Vorschau-Tool tools/preview_carton_motion.py/.html ergänzt.
  Erste Szene03-Vorschau JS-VM: Play, Reset, Timeline PASS; kein Browserrender-
  oder Physiknachweis. Quell-/Plan-/Szenenhash im Vorschau-Datensatz.
- Validator erkennt fehlenden Dreh-/Kontaktbeleg korrekt als INCOMPLETE/FAIL;
  eigener Bericht03/validator-negative-report.json. Keine Fremdrohdaten geändert.

## Kontaktversuche (keine Erfolge umetikettieren)

- contact01 ab Home: image-onlyOAK67Inlier/0,692px; Strategie nach Bildreview
  freigegeben. Alle Kandidaten vor Bewegung verworfen, mittiger Kandidat wegen
  dichter zeitparametrierter Anfahrtsprüfung. Unterstützt, beide Holds bestätigt.
- contact02 aus vorhandener Vorpositions-Fixture: OAK66Inlier/0,588px; vollständige
  Bildpose-basierte Hebe-/Dreh-/Absetzplanung PASS. 147,55mmHub/+90°/linkerTisch;
  56,44/249,14/61,30s Tragephasen. Alle12Gelenke unter0,04rad/s/0,25rad/s².
  Ausrichtung nach Anfahrt0,532mm/0,00596rad, OAK68Inlier/0,826px, Bilder geprüft.
- Beide Greifer erreichen echte zweiseitige Kontakte. Vor Lastübernahme Stopp
  durch STATE STALE: Empfangs-/Quellenfortschrittslücke0,170117s bei150ms Grenze.
  Kein Anheben/Drehen erfolgt. Karton unterstützt, vierPads und beide Holds
  erhalten; kein Öffnen beauftragt. Krafttrace vollständig,50N-Referenz unterschritten.
- Geplanter einzelner Wiederholungsversuch03: gleiche0,5ms-Physik, gleiche
  Grenzwerte und Strategie, nur RTF0,4 statt0,6 für mehr Echtzeit-Rechenreserve.
  Profil setup/tasks/carton_roll_rtf04_20261116.yaml. Nicht als Kräfteänderung
  oder Grenzlockerung interpretieren. Aktuell fremde Home-Reihe aktiv;
  wartender eigener Starter wait_carton_roll_retry_20261116.py startet erst
  nach Ende fremder Experimentdriver/Greifwelt und10s freier Prozesssicht.
  Keine fremden Dienste/Prozesse stoppen. Log uwa-carton-roll-contact03.log.
