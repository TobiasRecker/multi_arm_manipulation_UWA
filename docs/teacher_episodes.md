# Zielketten für den Zweiarm-Teacher

Stand: 2026-11-17. Reiner Offlineversuch; kein Netztraining, keine Ausführung.

## Verhalten und Lernformat

`tools/generate_teacher_episodes.py` erzeugt mehrere aufeinanderfolgende
Objektziele mit Translation und Rotation. Beide rechten Arme behalten ihre
festen Objekt→TCP-Transformationen; linke Arme bleiben Hindernisse.
Der **geprüfte tatsächliche Endzustand** eines Abschnitts ist exakt der Start
des nächsten. Keine Rückkehr zur Mitte, kein Rücksetzen der Gelenke und kein
Wechsel auf eine unabhängig berechnete Ziel-IK. Neue Ziele entstehen erst
nach dem Erreichen des vorigen Ziels. Zunächst gemeinsamer Stillstand an jedem
Ziel, mit verschwindender Geschwindigkeit, Beschleunigung und Ruck.

Die langen Episoden dienen der Zustandsabdeckung. BC behält lokale Eingaben
und Aktionen: 100 geometrische Übergänge je Ziel, aktueller Zustand und
aktuelles Ziel/Referenzvorschau. `goal_terminal` markiert ein erreichtes Ziel,
nicht das Ende der Gesamtaufgabe. Die Schrittweite ist Δs=0,01, **kein fester
Regeltakt**. Episoden-/Zielzuordnung steht im JSON-Bericht. Noch kein lernendes
Rollout und keine Aussage über Langzeitstabilität einer Policy.

## Tischvermeidung

`teacher_episode_core.EpisodeTeacher` ergänzt Arm/Tisch-Bedingungen im
Optimierer: Kugelhüllen der Ober-/Unterarme, Handgelenke, Greifer und
Wrist-Kameras gegen beide Tischboxen; Weltgradient über Gelenkjacobi und
gekoppelte Objektkinematik. Basis-/Schultermontagekontakt wird nicht als
zusätzliche Ausweichbedingung verwendet. **Keine neuen FCL-Ausnahmen.**

Optimierungsziel mindestens 4 mm Hüllenabstand, finale Annahmeschwelle 3 mm;
zusätzlich bestehende native FCL-Prüfung, mindestens 20 mm Armpaarabstand,
Karton/Umgebung und Karton/Armkörper, Griffschluss, Konditionierung und
Gelenk-/Ableitungsgrenzen. Das sind geometrische Versuchsparameter, keine
qualifizierten Hardwareabstände. Finale Interpolanten werden mit höchstens
5 ms Zeitabstand geprüft; zusätzlich die exportierten BC-Zustände.

Der frühere FCL-Tischfall `north-ik3-random-011` bleibt negativ. Die neue
Hülle misst auf dem Referenzweg bis −55,1 mm, **bereits am festen Ziel −30,8 mm**.
Das Ziel ist FCL-frei, aber unter der konservativeren Hüllenbedingung ungültig.
Der lokale Versuch `STALLED_INFEASIBLE` kann daher nicht allein durch einen
Umweg erfolgreich werden; Ziel/Hülle müssen zuerst geprüft werden. Dies ist
kein Nachweis globaler Unlösbarkeit oder eines Gradientenfehlers. Vier Proben
der gesamten Arm/Tisch-Ableitung stimmen mit zentralen Differenzen auf
höchstens 4,9e−10 überein. Der Episodenscreener verwirft solche Ziele vor
teurer Optimierung. Modellgeometrie ist teilweise konservativ; einige Links
haben im nativen Modell ausschließlich visuelle Geometrie.

## Geprüfter Pilot

Verzeichnis im Workspace: `setup/research/teacher-episodes-20261117/run01/`.
`viewer.html` zeigt ganze Episoden, Zielnummer, aktuellen Zielmittelpunkt,
Abstände, Play/Pause, Zeitschieber und drehbare Ansicht.

| Ergebnis | episode-000 | episode-001 |
|---|---:|---:|
| Erreichte Ziele | 6 | 6 |
| Modellzeit | 56,88 s | 47,99 s |
| Objektweglänge | 1,648 m | 1,023 m |
| Aufsummierte Orientierungsänderung | 249,2° | 190,1° |
| XYZ-Spannweite | 50,3 / 44,0 / 23,7 cm | 22,5 / 20,1 / 16,4 cm |
| Entfernung vom ursprünglichen Anker, maximal | 46,0 cm | 38,1 cm |
| Minimaler Armpaarabstand | 115,5 mm | 58,9 mm |
| Minimaler Arm/Tisch-Hüllenabstand | 27,6 mm | 27,6 mm |
| Dichte Prüfzustände | 11.384 | 9.607 |

Zustandsübergaben ohne Sprung, 1.200 exportierte BC-Übergänge. Generation
parallel auf zwei CPU-Workern/BLAS1/niceness10: 107,47 bzw. 92,51 s je Worker,
200 gescreente Vorschläge, 12 angenommene Abschnitte, kein verworfener
Teacher-Versuch unter den ausgewählten Abschnitten. Prüfungen/Auswertung
zusätzlich zur Generationszeit. 23 gezielte Tests inklusive vier neuer
Episodentests und zehn Browserchecks bestanden; Screenshot `viewer.png`
visuell geprüft. Testprotokoll im übergeordneten Verzeichnis: `tests.log`.

**Schwierigkeitsziel noch offen:** Keine der zwölf Referenzen kollidiert oder
verletzt den 20-mm-Armpuffer. Alle zwölf bleiben daher räumlich unverändert.
Der Screener nennt sechs Abschnitte `near`, weil seine breite Suchklasse
Armpaarabstände unter 80 mm umfasst; das sind keine sechs schwierigen
Ausweichaufgaben. `collision` ist eine Priorisierungsklasse für native Kontakte
oder negative Armhüllenabstände; `fcl_collision_samples` und tatsächlicher
Hüllenabstand bleiben getrennte Messwerte. Gewünschte Klassen werden versucht,
aber fehlende schwierige Kandidaten nicht als erfüllte Quote ausgegeben.

Der Pilot belegt längere, zustandsstetige Exploration und Tischprüfung. Für
den gewünschten überwiegend schwierigen Datensatz braucht es weiterhin
gezielte Grenzfallsuche mit gültigen Enden und erfolgreiche Teacher-Korrekturen.
Weitere identische Ketten allein lösen dieses Problem nicht.

## Wiederholen

Aus `~/UWA_ws`:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
python3 src/multi_arm_manipulation_UWA/tools/generate_teacher_episodes.py \
  setup/research/two-arm-diverse-starts-20261117/run01 \
  --output-dir setup/research/teacher-episodes-20261117/run02
python3 src/multi_arm_manipulation_UWA/tools/review_teacher_episodes.py \
  setup/research/teacher-episodes-20261117/run02
```

Standard: zwei deterministische Episoden mit je sechs Zielen. `--legs` und
`--maxiter` vor dem ersten Lauf festlegen; Manifeständerungen werden abgelehnt.
Ein vorhandenes Ergebnis wird wiederverwendet, eine unterbrochene Episode am
letzten validierten Endzustand fortgesetzt. Ohne gültiges Folgeziel wird die
Episode ausdrücklich beendet, nicht durch einen Reset repariert.

Basismodell und frühere Python-Quellen bleiben eingefroren. Eigener
Generationscode unter `code/`, aktualisierte Reviewer separat unter
`review-code/<SHA>/`; Manifest und Audit speichern die Bindungen.
`episode-audit.json` prüft Quellen, Exporte, Zielübergaben und Stillstand;
die dichten Geometrieprüfungen stehen pro Abschnitt im Episodenbericht.
`table-regression.json` und `table-gradient-audit.json` halten den negativen
Tischversuch getrennt vom positiven Episodenexport fest.

Alle Episoden bleiben `split: unassigned`. Ganze Episoden **und** verwandte
Start-/Zielfamilien gemeinsam gruppieren, einschließlich bereits vorhandener
Datensätze. Zwei unterschiedliche Episoden-IDs garantieren keine Unabhängigkeit.
Keine zufällige Verteilung benachbarter Übergänge über Training und Test.
