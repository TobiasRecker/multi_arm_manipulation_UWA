# Unterschiedliche Ausgangszustände für den Zweiarm-Teacher

- Status: abgeschlossen, 2026-11-17, Hauptagent dieses Chats.
- Nutzer bestätigt schwierige Begegnungen als nächsten Schwerpunkt und
  bemängelt den praktisch gleichen Start aller bisherigen Abläufe.
- Auftrag: offline deutlich verschiedene Objektstartlagen/Armkonfigurationen
  ermitteln, neue Ziele von dort planen und Startvielfalt/Engstellen auswerten.
  Keine Hardware-/Kamera-/Dienstaktion; kein Training.
- Neue Module/Tools/Tests und kleine Ergänzungen in AGENTS/HANDOVER/README.
  Bestehende gebundene Pilotquellen unverändert lassen. Andere aktive Arbeiten
  an Hardwarezustand, Stoppreserven, OAK und Programmierpipeline erhalten.
- Höchstens zwei CPU-Worker, BLAS1/niceness10. Initialzustandsprüfung ist kein
  Nachweis einer Anfahrt/Griffherstellung. Alternatives IK nicht mit unabhängig
  frei wählbaren Armen bei starrem Griff verwechseln.

## Ergebnisse

- ZwölfvorabfestgelegteStartfamilien, neunmitgültigenZuständen, je2–12gültige
  IK-Kombinationen. run01:13/24BahnenausachtStarts,1.300BC-Übergänge,
  tatsächlicheStartabdeckung32×32×10cm/125°,mindestens13,4cmvomaltenAnker.
- GezielteZusatzdiagnoseencounters01:4/6Bahnen,400Übergänge. TragendeRF/RR-
  Armhüllabstände15,82/5,64mmzuje21,00mmkorrigiert; max2,05/4,74mmund
 1,17/3,48°Korrektur. KeineFCL-KontaktkollisionderReferenzenbehauptet.
- UnveränderteStart-/Endposen, Eltern-Hashes/Splitsübernommen, separate
  Diagnoseauswahl. AlleFehlversucheerhalten. KeinTraining/keineGeräteaktion.
- Build/18gezielteTests/beideExportaudits/199+73BrowserchecksPASS,
  Screenshotsvisuellgeprüft. BeideWiederaufnahmeläufeExit0ohneNeuberechnung.
  ErsterEncounterprozessmeldetenachvollständigemSUMMARYspäterExit143;
  allesechsFallberichtevorhandenundanschließendperHash/Audit/Wiederaufnahme
  geprüft. UrsachederProzessbeendigungnichtbestimmt, keinfehlenderFall.
- Dokumentationdocs/teacher_start_diversity.mdundHANDOVERaktualisiert.
  Weiteroffen: ausgewogenergrößererTrainings-/Testkorpus; positiverMisch-
  TrainanteildiesesHauptlaufsleer, neueArmkorrekturenerbenTestsplit.
