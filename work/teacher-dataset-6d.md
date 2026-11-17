# Gemischte 6-DoF-Lehrerbeispiele für BC

- Status: abgeschlossen, 2026-11-17 (Australia/Perth), Hauptagent dieses Chats.
- Nutzer beauftragt mehr Teacher-Bewegungen; mehrere Rotationsachsen und
  Translation gleichzeitig variieren. Getrennte Translations-/Rotations-/
  Mischnetze sind eine offene Frage, keine getroffene Nutzerentscheidung.
- Technische Empfehlung: gemeinsame6D-Policy, getrennte Referenzaufgabenklassen
  translation3d/rotation3d/mixed6d im Datensatz und in der Auswertung.
  Auch reine Referenztranslation darf eine Rotationskorrektur benötigen.
- Umsetzung: reproduzierbare Aufgabenfamilien, vorab fixierte Familien-Splits,
  wiederaufnehmbarer Offlinebatch und nur aus vollständig geprüften Bahnen
  exportierte geometrische BC-Übergänge. Noch kein Netztraining.
- Bereiche: neue Datasetmodule/CLI/Tests, Anleitung/README/AGENTS/HANDOVER;
  bestehende Teacher-Kernquellen und alte Prüfnachweise möglichst erhalten.
- Lokaler Batch höchstens zwei normale CPU-Worker, niceness10, je ein BLAS-
  Thread. Keine Roboter-/Kamera-/Dienstaktionen; aktive OAK-Arbeit erhalten.

## Umsetzung / laufende Prüfung

- Neue Module `teacher_dataset.py`, `tools/generate_teacher_dataset.py` und
  `tools/review_teacher_dataset.py`; bestehender Teacherkern unverändert.
- 32 vorab fixierte Aufgaben aus16Familien, zweiVarianten jeFamilie;
  8Translation/8Rotation/16gemischt,16/8/8Aufgaben Train/Validierung/Test.
  Pro positiverBahn100geometrischeÜbergänge (Δs=0,01),52Beobachtungswerte,
 6D-Weltposeaktion. Referenzausblick enthält keineLehrerkorrekturen.
- BuildPASS,15gezielteTestsPASS; Exportauditund309BrowserchecksPASS,
  Screenshotvisuellgeprüft. Wiederaufnahmeerkennt32/32fertigeFälle.
- `pilot01` abgebrochen: Versionsbindung umfasste unnötig alleMotionmodule.
  Parallel geändertes `hardware_state.py` wurde dadurch fälschlich als
  ÄnderungdesOfflinealgorithmus erfasst. Zehn bereitsgeschriebene positive
  Fälle bleibenhistorisch, nichtinfinalenDatensatzübernommen. Bindungjetzt
  auf19relevanteAlgorithmus-/Modellquellen begrenzt; keineFremddateigeändert.
- Neuer vollständigerLauf `setup/research/two-arm-teacher-dataset-20261117/pilot02/`,
  identischeAufgaben/Seed, höchstens30SQP-Iterationen. Abgeschlossen21/32gültig,
  zehnkorrigiert/elfReferenz-IK-Fehler,2.100BC-Übergänge. Export-/Galerieartefakte
  direktinpilot02. 48.859Zeitprüfpunkte≤5ms,2.121ExportzuständePASS.
- Abdeckungslückendokumentiert: positiveRotations-Testgruppeleer, akzeptierte
  Mischtestbahnenbereitsfrei; neueAusweichfällebetreffenKarton/Umgebung,
  keineengenArm/Arm-Begegnungen. KeinTrainingundkeineGeneralisierungbehauptet.
- DauerhafterStandinHANDOVERunddocs/teacher_dataset_6d.md; keineDienstneustarts.
