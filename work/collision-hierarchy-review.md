# Hierarchische Kollisionsprüfung untersuchen

- Status: **Vorfilter implementiert und offline geprüft**, 2026-11-16 (Australia/Perth), Hauptagent.
- Nutzer schlägt mehrstufige Hüllen vor: ganzer Arm, Glieder, feine Kugeln;
  Motivation weniger Rechenaufwand bei weit voneinander entfernten Robotern.
  Nachfolgend ausdrücklich beauftragt: zuerst den Arm-Hüllquader-Vorfilter umsetzen.
- Bereiche: uwa_cell_motion/geometry.py, gemeinsamer boolescher Planercheck,
  native RRT-Reserveprüfung, gezielte Tests/Offlinebenchmark, Projektdokumente.
  Exakte nächste Abstände/Gradienten, Laufzeitwächter und Schwellen erhalten.
  Fremde Greifpipeline erhalten; keine gemeinsamen Dienstneustarts/Roboterfahrten.
- Code geprüft: MoveIt/FCL hat Broadphase/BVH; zusätzliche SphereModel.nearest-
  Prüfungen und native RRT-Reserveprüfungen berechnen bisher alle Kugelpaare.
  CDF-Kontakt-SDF ebenfalls dichte Körper/Hindernisabstände; CDF-Onlinequery
  dagegen bereits Präfix-KD-Trees im Gelenkraum. Aufgaben unterscheiden.
- Lesendes Offline-Mikroprofil von150Zuständen des vorhandenen RR-CDF-Wegs,
  drei andere Arme eingefroren,54Kugeln/Arm. Je Zustand ca.0,524ms FK/Kugeln,
 0,115ms FCL,0,333ms vier zusätzliche Kugelpaar-Abstandsabfragen. Ein Beispiel,
  kein allgemeines Laufzeitprofil oder gemessener Planer-Speedup.
- Basiszentrierte Kugeln aus aktueller Pose verwerfen0/600Nachbarpaarabfragen;
  vollständige posespezifische Kugel-AABBs verwerfen587/600 unter gleicher
  Abstandsschwelle. Glieder-AABB-Test lässt1573von1749600feinen Kugelpaar-
  Kandidaten übrig, ohne Einbeziehung der Kosten dieses Vorfilters.
  Ergebnis setup/logs/uwa-collision-hierarchy-profile.json und zugehöriges.log.
- Empfehlung: zunächst gecachte Hüllen der unbewegten Arme und enger Arm-AABB-
  Vorfilter, danach ggf.Gliederhierarchie; gegen identische Zustände/Entscheidungen
  und Gesamtzeit messen. Elternhüllen müssen ganze Volumina/Tools/Reserven
  umfassen. Überschneidung ist nur Kandidat. Boolesche Schwellenprüfung von
  exakter Nächstabstands-/Gradientenanfrage unterscheiden; keine CDF-Feldwerte
  pauschal wegfiltern. Intervallfreigabe braucht Bewegungshüllen zwischen Punkten.
- Umsetzung: gemeinsamer Python-Planungscheck und nativer RRT-Worker nutzen
  Arm-AABBs über vollständige Kugelvolumina, nach außen gerundet. Grober
  Abstand muss Schwelle plus numerische Reserve überschreiten; sonst alte
  Feinprüfung. Exakte Wächter-/Gradienten-/CDF-SDF-Abfragen unverändert.
- Cache pro Modell/Arm an gesamte bewegliche Vorfahren/Mimic-Quellen gebunden,
  einschließlich Greifer; unvollständige/nichtendliche Daten vor Cache geprüft.
  Native feste Arme pro Anfrage gecacht, alle aktiven Abhängigkeiten berücksichtigt.
- Build und120Paketchecks PASS, einschließlich11neuerPythonfälle/270Zuständen
  aus30Aufgaben und3000zufälligen nativen Wolkenpaaren plus Schwellenfällen.
  Hardware-Öffnungshüllen/Greiferinvalidierung/exakte Wächterwerte geprüft.
  Logs setup/logs/uwa-prefilter-{build,tests}.log.
- Gemessener Offlinevergleich mit5rotierten Wiederholungen:
  Trajektoriencheck1,051→0,734ms/Zustand(30,2%wenigerZeit), fixeSuite
 1,035→0,771ms(25,5%). CDF-Gesamtplanung3,112→2,304s bei exakt identischer
  zeitparametrierter Bahn; Kontaktbankvorbereitung nicht Teil dieses Gewinns.
  Ein nativerRRT-Lauf6,913→1,194s, beide Wege vollständig nachvalidiert;
  keine allgemeine5,8×-Garantie/identische RRT-Wege behaupten.
- Bericht setup/research/aabb-prefilter-v1/report.html und result.json,
  wiederholbares Skript uwa_cell_motion/test/benchmark_prefilter.py. Anleitung
  docs/collision_prefilter.md, AGENTS/HANDOVER/README gepflegt. Keine neuen
  Dienste oder Roboteraktionen, keine gemeinsame Simulation neu gestartet.
