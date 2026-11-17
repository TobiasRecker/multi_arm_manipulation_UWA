# Allgemeine Überarbeitung der Stoppreserve

- Status: **Implementierung, Offlinevergleich und getrennte Mock-Integration
  abgeschlossen**. Hardwareprofile nicht aktiviert; reale Aufnahmestellungen
  weiterhin ausstehend. 2026-11-17 (Australia/Perth), Hauptagent dieses Chats.
- Nutzer möchte nach72min vorgeschlagener Kalibrier-Anfahrt die Berechnung
  generell überarbeiten. Ursache: temporäre0,004rad/s-Kommandogrenze als Behelf
  gegen pauschale Reserve, alle Gelenke jedes Arms an Obergrenze und ein
  globales Maximum je Arm. Das ist keine physische UR-Leistungsgrenze.
- Während dieser Arbeit keine realen Fahr-/Power-/Brake-/Play-/Greiferaktionen.
  OAK-GUI, vier vorhandene Treiber und MONITOR-ONLY-Dienst erhalten.
- Bereiche: common.py/geometry.py/guard_core.py/planning.py/interlock.py,
  hardware_model.py, neue Rechenkern-/Regressionstests und Offlinevergleich.
  Laufende fremde hardware_state.py-/RT-Stopptest-/Teacheränderungen erhalten.
- Neuer Ansatz opt-in: einzeln überwachte Gelenkgrenzen, explizites
  Kommandotempo, Reserve pro Körper und Prüfung sämtlicher Kugelpaare;
  schlechteste Restreserve und kürzeste Ausfall-Lease getrennt bestimmen.
  Stillstehende physische Arme behalten positive überwachte Grenzen. Bereits
  vollständig eingeschlossene virtuelle Greiferöffnung nicht nochmals bewegen.
  Alte Profile/aktive Prozesse bleiben bei alter Rechnung. Modellreserve,
  Frische, angenommene Latenz/Bremsung nicht still verkleinern.
- Nachweis: analytische/randbasierte Rechentests, Signatur-/Frische-/Lease-
  Regressionen, bisherige Hardware-/Planungstests, vier reale eingefrorene
  Sichtwege offline vergleichen. Kein Stoppqualifikationsnachweis daraus ableiten.

## Ergebnis und Prüfnachweise

- Folgeauftrag: Nutzer beanstandet weiterhin9,2min und schlägt0,1rad/s vor,
  Nothaltzugriff laut Nutzer vorhanden. Zeitvergleich derselben Wege bei0,1:
  LF47,87s/LR39,02s/RR56,85s/RF29,53s, insgesamt173,27s/2,89min bei unverändert
  0,02rad/s² Beschleunigung. Das ist reine Zeitparametrisierung, kein bestandener
  Stoppreservetest. Quelle speed-0p1-time-only.json im Kalibrierordner.
- Erkannt: v2-Audit verwendet weiterhin eine konstante Grenzmatrix für eine
  ganze Armfahrt. Die kurze enge Anfangszone links hinten drosselt damit den
  gesamten Weg auf0,01364rad/s. Lokale Zeitparametrisierung/Phasenverträge und
  belastbare Stoppannahmen bleiben als nächste Verbesserung offen.
- Paralleler right_front-RT-Stopptest laut Arbeitsstatus in Durchführung;
  dessen Steuerdienst/Arm nicht übernehmen. Diese0,1-Prüfung bleibt offline,
  keine reale Grenzänderung oder Fahrt. Diagnosesensitivitäten verstellen keine
  operativen Latenz-/Bremsparameter.
-0,1-Sensitivität abgeschlossen, Artefakt speed-0p1-diagnosis/summary.json:
  mit bisheriger1sAnnahme bestehen die Reservegrenzen links vorne/hinten rechts,
  links hinten und rechts vorne nicht. Bei hypothetisch50ms bleibt links hinten
  ebenfalls abgelehnt. Ursache also nicht nur Latenz: Datenalter-/Prüftaktbudget,
  angenommene0,2rad/s²Bremsung, Trackingzulage und konstante Grenzmatrix über
  den ganzen Weg bleiben wirksam. Negative Restreserve ist kein nachgewiesener
  geometrischer Kontakt. Sensitivität mit0,1Kommandokandidat und bis0,132
  überwachten Achsgrenzen; keine Behauptung einer harten0,1-Istgrenze.

- Opt-in-Modus `per_body_joint_caps_v2` umgesetzt, einschließlich gemeinsamer
  Timingfunktion für Planung/Ausführung, einzelner Achsüberwachung, vollständiger
  Kugelpaarprüfung und kürzester Ausfall-Lease über alle Körperpaare. Alte
  Profile behalten ihre bisherige Rechnung. Anleitung: docs/stopping_reserve.md.
- Dieselben vier geometrischen Sichtwege:4331,70s/72,19min →554,60s/9,24min.
  Neue Einzelzeiten LF95,74s/LR286,09s/RR113,70s/RF59,07s. Modellpuffer40mm,
  Stoppannahme1s, Bremsannahme0,2rad/s²,10Hz und Frischegrenzen unverändert.
  Referenz: setup/calibration/oak_recalibration_20261117/reserve-v2-audit-02/.
- Build und registrierter CTest PASS; vollständige268Motiontests PASS,
  abschließend31gezielte Tests PASS (einschließlich zusätzlicher Prüfung der
  analytischen Zwischenpunktabdeckung im Audit). Logs: setup/logs/uwa-reserve-v2-*.
- Getrennte Fake-Prozesse/Domain67 PASS: Bewegung mit Achsgrenzen, eingefrorene
  Quelle stoppt Nachbarn, keine automatische Wiederaufnahme, Ausfall jeweils
  von Guard/Watchdog/Supervisor hält alle vier. Ergebnis:
  reserve-v2-process-mock-02/result.json im obigen Kalibrierordner.
- Frühere Einprozess-Mockfehler und erster Neustart-Test erhalten: Teilreset-
  Erwartung, Datenfrische unter Last und vorzeitig gestellter Test-Reset.
  Nur Testvorbereitung korrigiert; produktive Frische-/Resetgrenzen unverändert.
-100Offline-Geometrieaufrufe: Median3,78ms, Maximum4,02ms; kein Nachweis einer
  ROS-Ende-zu-Ende-Frist oder realer Stoppstrecke. Physical-Stop-Qualifikation
  bleibt offen. Keine realen Fahr-/Power-/Brake-/Play-/Greiferbefehle dieser Revision.
