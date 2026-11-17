# Kraftvergleich desselben Ablaufs bei1× und5×

- Status: Hub-Kraftvergleich abgeschlossen; volle5×-Drehung offen, 2026-11-17 (Australia/Perth), Codex dieses Chats.
- Auftrag: simulierte Kontaktkräfte bei fünffacher Robotergeschwindigkeit
  vergleichen, gleiche Bahn/Mechanik; tatsächliche Physik statt schnelleremReplay.
- Bezug: geplantes90°-Drehrezept. Neuer vertikaler5×-Zyklus vollständig;
  vollständigeDrehung weiterhin offen. Abbrüche erhalten. Hardware und fremde Simulationen unangetastet.
- Vorprüfung: globale konservative Hüllreserve auch mit realistischen proDOF-
  Geschwindigkeitsmaxima reicht für vollständige5×-Drehung nicht (bis37mmFehlreserve).
  Kein Abschalten. Messbare Teilprüfung: identischer147,812mmHub und Rücksetzen
  bei1×/5×, ohneDrehung; vollständigeDrehung getrennt als nicht freigegeben melden.
- Zeitkompression für alle12Tragegelenke gemeinsam: t/5,v×5,a×25,jerk×125.
  Greif-/Einfahrbewegung, Masse/Reibung/Preload/Physikschritt gleich. Strikte
  perGelenk-Grenzen samt vollständigerStoppreserve werden vorab gebunden.
- Bereiche: optionale Skalierung/Explorationsdaten imTaskpaket, Tests, eigene
  Vergleichsskripte/Artefakte/Docs. Aktive Offline-Zielkandidatenarbeit erhalten.

## Umsetzung und erste Messung

- Optionale `carrying_speed_multiplier` skaliert alle12Gelenke und Objektposen
  gemeinsam in der Zeit. Positionen bleiben bytegleich; tatsächliche JTC-
  Polynomextrema für Geschwindigkeit/Beschleunigung sowie Ruckgrenze geprüft.
- Explizite `joint_velocity_overrides_rad_s` nur für die12rechten Armgelenke,
  vollständig in strikter Laufzeitprüfung und geometrischem Bremsbudget.
  Finger-/Fremdarmgrenzen bleiben erhalten. Vergleichs-Hubprofil trägt bis
 147,8116949mm, ohneDrehung, mit vollständigem Vorabzeugen für Hub/Rücksetzen.
- Tests70Pythonfälle PASS einschließlich vorhandener Hardwarevorbereitungstests;
  Lyrical-Paketbuild PASS. Erster Testaufruf vorNeuinstallation hatte alte
  installiertePythonmodule, Importfehler erhalten; nachBuild alle70PASS.
- 1×-Kontrolle: vorhandener vollständiger Hub aus
  carton_roll_contact_20261116_03/case00/run, exakt56,5379733s Sollzeit;
  Auswerteuhr aus gemessenen Gelenken gegen geprüfte Bahn bestimmt,
  90%-Spannweite nur39,6µs,5653native Kraftfenster ohneLücke imHub.
- Neue5×-Bahn:11,3075947sHub und Rücksetzen, maxJTC0,057385rad/s und
 0,015983rad/s². Gleiche500g/Reibung0,6/Motor30Nm/rad0,7Nm/Physik0,5ms.
  Gemeinsame proGelenk-Hüllreserve imHubvorfilter mindestens17,77mm.
- fast-attempt01 vorBewegung mit TASK RUNNER LOST währendPlanreview gestoppt;
  beideHolds bestätigt, unterstützt. Keine5×-Kraftmessung daraus ableiten.
  Wiederholung fast-attempt02 mit unveränderten Parametern aktiv; Bild-, Plan-
  und Ausrichtungsreviews jeweils explizit durchgeführt. Quellen bleiben stabil.

## Native Begrenzung entdeckt und korrigiert

- fast-attempt02 verlor bei ca35,45mm Hub die RF/linkeBacke, aber ist **kein
  gültiger5×-Kraftvergleich**: nativesContactArms max_velocity blieb0,04rad/s,
  während die geprüfte Bahn0,0574rad/s verlangte. GemesseneWrist1-Geschwindigkeit
  exakt0,04; Zeitfit90%-Spannweite32,76ms statt39,6µsderKontrolle. Unterschiedliche
  Gelenke wurden verschieden stark abgeschnitten, starre Koordination verzerrt.
- Erste Kurven/Rohdaten bleiben als Fehlerdiagnose erhalten; Vergleich01 ist
  durch INVALIDATED.json ausdrücklich zurückgezogen. Nicht als Physikgrenze
  oder Geschwindigkeitseinfluss auf Kraft zitieren.
- Fehlerursache in eigener neuer Datenanbindung: Szenengenerator übergab nur
  skalarePlanungsgeschwindigkeit an nativenTreiber. Jetzt nativeMaximalgrenze
  als Maximum der expliziten proGelenk-Grenzen; strikte einzelneGrenzen bleiben
  imWächter. XML-Regression prüft0,065rad/sstatt0,04;85Tests nachaktuellemBuild PASS.
- fast-attempt03 nutzt eingefrorenen korrigiertenExperimentstand unter frozen/
  mit COLCON_IGNORE. ParalleleHardware-/Offlinearbeiten werden nicht verändert
  und können diese Quelle nicht mehr währenddesLaufs invalidieren.
- Vergleichsauswertung fordert nun <5ms Zeitfitspanne und nicht erreichte
  nativeGeschwindigkeitsgrenzen. Mechanik/Geometrie/Inertien/Engine-/Backend-
  Binärdateien werden zwischen1× und5× geprüft. TatsächlicheTracking-/Kontakt-
  Fehler vorvollständigemHub werden nicht als vollständigerVergleich ausgegeben.

## Planungsstatusmeldungen stabilisiert

- fast-attempt03 ebenfalls vor Bewegung mit TASK RUNNER LOST gestoppt; Quellen
  waren eingefroren und unverändert, beideHolds bestätigt. Kein Kraftvergleich.
- Lange nativePolynomkonvertierungen jetzt in128Segment-Blöcken mit gemeinsamem
  Randpunkt. Gleiche exakte segmentweiseJTC-Polynome/Extrema; keine Frist oder
  Kollisions-/Kontaktgrenze gelockert. Regression über270Punkte,3Ableitungen
  gegen monolithischeBerechnung PASS (6gezielteTimingtests PASS).
- Vollständige Offline-Rezeptkompilierung einschließlich Modellerzeugung,
  Versiegelung und15MB-Planexport: unabhängiger5msTicker, längstebeobachtete
  Pause75,8ms. Dies ist ein einzelnerPlaner-Stresstest, keineEchtzeitgarantie.
- fast-attempt04 nutzt frozen02/ mit dieser Änderung; normaleQuellen bleiben
  parallel bearbeitbar. Reviewstrategie nach Bildern/livefaults[] angenommen.
- fast-attempt04 bestand Planung und alle dreiReviews, dann STATE STALE
  (150,7ms Empfangslücke) inGrasp vor Hub. Vier Kontakte blieben erhalten,
  Endzustand bestätigteHolds; eigeneWelt vomDriver beendet. Keine5×-Hubmessung.
- fast-attempt05: ausschließlich Echtzeitfaktor0,4→0,2 reduziert, um die lokale
  Rechen-/Transportreserve zu erhöhen. Weiterhin0,5msPhysikschritt und exakt
  5×Bewegung inSimulationszeit; andereMechanik-/Greifparameter unverändert.

## Gültiger Vergleich und Abschluss

- fast-attempt05 DONE:147,738mm tatsächlicherCOM-Hub, Rücksetzen/unterstütztes
  Lösen undHolds bestätigt; Validierung/Kraftabdeckung PASS. Relativfehlermax
 0,373mm, vierPads beimTragen erhalten. EigeneWelt/Runner/Recorder beendet,
  Host-Prozessprüfung ohneGreifprozesse; fremdeHardware-/Offlinearbeit erhalten.
- Maßgeblich comparison-final/result.json undforces.png. GemeinsamerHubbereich
 99,947%;5653/1130Kraftfenster lückenlos. Identische2263Gelenkstützpunkte bis
 1,70e−13rad; t/v/a-Skalierung numerisch nachgewiesen. Sollzeit56,538→11,308s;
  gemesseneArmgipfel0,011477→0,057567rad/s, kein nativerCap erreicht.
- Max10ms-Mittelobergrenzen1×→5×: RFlinks4,887→4,965N(+1,60%),
  RFrechts4,506→4,699N(+4,28%), RRlinks5,160→5,151N(−0,17%),
  RRrechts4,559→4,564N(+0,10%). GrößtePhysikschritt-Peakobergrenze
 5,162→5,401N(+4,63%). Material/Engine/Backend/Geometrie/Inertien gleich;
  Echtzeitfaktorunterschied explizit dokumentiert. Einzelvergleich ohneStatistik.
- VollständigeDrehung nichtausgeführt; erste5×Stufe bewusst nurHub. Starrmodell
  beweistkeineQuetschfestigkeit oderrealeHardwarekapazität.
- 95TasktestsPASS, LyricalTaskbuildPASS; Logs *speed5-{tests,build}-final.log.
  Dokumentation docs/carton_speed_comparison_2026-11-17.md. Zwischenberichte02–04
  sind gültigeDatensatz-Auswerteentwicklungen; final ersetzt ihreMetadaten.
