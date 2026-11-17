# Programmierpipeline und Lernen aus Demonstrationen

- Status: Präzisierung in Arbeit, 2026-11-17 (Australia/Perth), Codex dieses Chats.
- Folgeauftrag: Task-Level Code as Policy mit Halte-/Bearbeitungsrollen;
  vorhandene32/21Kollisionsbeispiele sind ausdrücklich ein anderes Problem.
  Agent führt in Simulation vor, Nutzer bewertet/korrigiert oder übernimmt
  perTeleop. Langfristiges Lernen aus eigenen Ausführungen plus Feedback für
  wiederkehrende Industrie-/Bauaufgaben einplanen. Kein Hardware-/Trainingsauftrag.
- Auftrag: vorhandene MRS-Programmierpipeline prüfen; Literatur zu wenigen
  Demonstrationen plus Sprache recherchieren, Übernahmen und Lücken bewerten.
- Nutzerziel: schnelles einfaches LLM komponiert Aufgabenprogramme; optionale
  Teleoperations-/Handführungsbeispiele mit Kameras, UR-Zuständen und Kräften.
  Keine vollständige neue Policy als Voraussetzung.
- Bereiche: neuer Forschungsbericht unter docs/, kleine ergänzende Einträge in
  AGENTS.md/HANDOVER.md/README.md; bestehende parallele Änderungen erhalten.
- Keine Dienstneustarts, Kamera-/Roboterzugriffe, Trainings- oder Fahraktionen.
- Ergebnis: docs/programming_pipeline_lbd_review_2026-11-17.md mit Bestandsaufnahme,
  neun eingeordneten Forschungsansätzen, gemeinsamer Aufgabenbeschreibung,
  Aufnahmeanforderungen, priorisierten Integrationsschritten und Vergleichspilot.
- Besonders passend: ShowTell/Demo2Code für Aufgabenprogramme, DROC für Korrekturwissen;
  Bewegungs-/Kraftmodelle ergänzen einzelne Skills. Neue ACE-CaP-0-Studie ausdrücklich
  als Preprint und ohne Nachweis eines schnellen kleinen Modells eingeordnet.
- Bestehende pilot02-summary/export-audit gelesen: 21/32 akzeptiert, 2100Übergänge,
  stored passed:true; keine Nachprüfung der Trajektorien oder neues Training behauptet.
- AGENTS/HANDOVER/README um Nutzerziel, Empfehlung und Berichtverweis ergänzt.
  Bestehende Änderungen einschließlich paralleler OAK-/Teacher-Arbeit erhalten.
- Prüfung: git diff --check der geänderten Bestandsdokumente erfolgreich;
  sämtliche relativen Links des neuen Berichts vorhanden. Nur Dokumentation,
  keine neuen Software-/Hardwaretests erforderlich oder durchgeführt.
- Nächste Entwicklung: Aufgabenformat/Interpreter, Offline-Demoimport und
  zeitqualifizierter Recorder; dies sind Empfehlungen, kein Implementierungsbeschluss.
