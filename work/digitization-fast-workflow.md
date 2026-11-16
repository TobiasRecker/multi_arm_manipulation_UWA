# Digitalisierung für einen schnellen ausführenden Agenten vorbereiten

- Status: **Offline-MVP fertig, reale Mehransicht durch Nutzer unterbrochen**, 2026-11-13,
  Hauptagent Digitalisierung.
- Nutzerziel: deutlich kürzere Durchlaufzeit mit geringerem Reasoning-Aufwand,
  geprüfte Qualität und bestehende Sicherheitsfunktionen erhalten.
- Neuer Auftrag: Pipeline implementieren und an studentischem Roboternachbau
  testen, laut Nutzer ungefähr330×300×330mm. Mehrere Wristansichten erforderlich.
  Geometrieklasse unbekannt; keine erzwungene Kasten-/L-Rekonstruktion.
- Umfang: wiederaufnehmbare Pipeline, Daten-/Qualitätsverträge, Skill und
  Offlineprüfungen; aktuelles OAK-Bild, kameraseitige Bestandsaufnahme,
  neue objektbezogene Ansichtsvorbereitung. Keine ungeprüften alten Scanwege.
- Bereiche: neue Digitisierungswerkzeuge/Tests/Skill, Aufnahme-/Planungsadapter,
  docs/digitization_pipeline_plan.md, AGENTS/HANDOVER/README.
- Keine Leistungswerte versprechen: technische und agentbedingte Zeit getrennt
  messen; heutige objektspezifische Skripte nicht als universelle Pipeline ausgeben.
- Parallele Greif-, Planungs- und FoundationPose-Arbeit erhalten.
- Nutzer13.11.: URs für Meeting ausgeschaltet; ausdrücklich nur offline
  weiterarbeiten, bis er sie wieder einschalten kann. Keine weiteren Netzwerk-
  abfragen/Restore-/Bewegungsversuche an URs während dieser Unterbrechung.
- OAK-Übersicht aufgenommen. Erster Fünfersatz vor Bildern an Telemetrieaufbau
  abgebrochen; zweiter Satz dreiWrist-HD+OAK, LF-SSH nicht erreichbar und
  HTTP-Restore beim Abschalten fehlgeschlagen. Beide Versuche unvollständig
  erhalten, kein erfolgreicher Audit-/Restore-/Mehransichtsnachweis behaupten.
- Bestandsbefund und Abnahmeplan in docs/digitization_pipeline_plan.md,
  Nutzerziel in AGENTS/HANDOVER und README-Verweis gepflegt.
- Implementiert: wiederaufnehmbare Jobs, parametrisierte Schalen-/Plattenform,
  eingefrorene Optik/Prüfregeln, Texturflächendaten, technische CAD-Kandidaten,
  held-outTrackingcheck, lesbarer Status und eigene kurze Skill.61Tests/Build PASS.
- Ein `run`-Aufruf bündelt Offlinearbeit; PTFE mit fertigen Annotationen7,18s,
  Cachewiederholung1,33s inklusiveCLI-Start. Qualität weiterhinREVIEW_REQUIRED;
  keine neue Aufnahme oder unbekannte Formanalyse in diesen Zeiten enthalten.
- Offline-Replays beider echter Objekte abgeschlossen; ursprüngliche Qualitäts-
  grenzen/Fehlschläge erhalten. Kein dichter Mesh-Backend oder Vergleich
  niedrigerer Reasoning-Stufen behauptet. Aktuelle Anleitung digitization_workflow.md.
- Studentischer Roboter: OAK-basierte Planungshülle und12modellgeprüfte
  Abschnitte für3Wristansichten je Arm vorbereitet; historische Startwerte,
  keine Hardwarefreigabe oder Realfahrt. docs/student_robot_digitization.md.
