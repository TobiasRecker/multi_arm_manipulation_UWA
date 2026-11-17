# Hierarchische Prüfung mit körperbezogenen Stoppreserven

- Status: abgeschlossen – integriert, gemessen und Regression bestanden,
  2026-11-17 Australia/Perth, Hauptagent dieses Chats.
- Nutzer fragt nach Verwendung der neuen Kollisionsmethode und wünscht sie
  künftig samt gemessener Berechnungsdauer. Annahme: Arm-AABB-Vorfilter16.11.;
  Bestätigung angefragt. Bisher wurde dieser im neuen v2-Planungszweig umgangen.
- Bereiche: geometry.py/Problem.check, gezielte Gleichheitstests, Offline-
  Benchmark mit eingefrorenem aktuellemLF-Plan, docs/collision_prefilter.md,
  AGENTS/HANDOVER. Fremde Änderungen erhalten.
- Körperweise Stoppbudgets in Elternhüllen aufnehmen; bei nicht bewiesener
  Trennung unveränderte exakte Feinprüfung. Cache nur zustandsgebundene
  Geometrie. Laufzeitwächter/Schwellen/Geometrie/Nativsicherheit unverändert.
- Keine reale Bewegung, kein Reset/Profilwechsel/Dienstneustart. Ausstehende
  konkrete q6-Freigabe bleibt separat und ungegeben.

## Nachweise

- Gemeinsamer v2-Planungscheck nutzt automatisch zustandsgebundenen Geometrie-
  Cache und konservative Arm-AABBs um Kugeln samt jeweiligem Stoppbudget.
  Unklare Paarungen laufen durch dieselbe critical_pair-Feinprüfung; exakte
  Wächter-/Leaseabfragen unverändert. Keine geänderten Modell-/Profilbindungen.
- 50gezielteTestsPASS:600variableKugelwolkenfälle, Schwellenfälle,
  geänderteBudgetsbeigleicherGeometrie,100Hardwarehüllen-Zuständeplusbisherige
  Vorfilter-/Reserveprüfungen. GesamteMotion-Pytests316PASS/19,04s.
- AktuellerLF-Plan01e,166Kugeln/Arm,150identischeZustände×3rotierteWiederholungen:
 5,316→2,294ms/Zustand;600/600Paaranfragenhiergrobalssichererkannt.
  KomplettePlanungjeeinLauf20,182→10,074s, geometrischerAnteil2,567→1,144s,
 895zeitparametriertePunkteexaktidentisch. ZusätzlicherModellaufbau1,471s.
  Einzelbeispiel, keineallgemeine2×-Garantie; Fahrdauer47,89sunverändert.
- Quelle setup/calibration/oak_recalibration_20261117/body-prefilter-benchmark-01/result.json;
  wiederholbarübertest/benchmark_body_prefilter.py. Logs
  setup/logs/uwa-body-prefilter-{tests,benchmark,regression}.log.
- InstallierteSymlink-ModulewurdenimBenchmarktatsächlichverwendet; keine
  Binär-/CMakeänderungundkeinDienstneustartnötig. gitdiff--checkPASS.
