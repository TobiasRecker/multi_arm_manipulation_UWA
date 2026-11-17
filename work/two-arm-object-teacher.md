# Zweiarm-Objekttransport als BC-Lehrer

- Status: abgeschlossen – erster Offline-Lehrer und geprüfte Beispiele,
  2026-11-17 (Australia/Perth), Hauptagent dieses Chats.
- Nutzer bestätigt Behavioral Cloning; zuerst Lehrer und gute Lernbeispiele.
  Zwei Arme halten gegenüberliegende kurze Kartonseiten. Objektposition und
  besonders Orientierung variieren, Bahnen optimieren. Langfristig Montage:
  zwei Arme halten Teil1, einer Teil2, einer Werkzeug.
- Zunächst rein offline mit festen Basen und hypothetisch starren Griffen.
  Übrige Arme bleiben modellierte stationäre Hindernisse, keine Realaktion.
- Bereiche: object_transport.py selektierbare Greifgruppe; neuer Zweiarm-
  Lehrer/CLI/Tests und eigene Vorschau/Artefakte; AGENTS/HANDOVER/README/Doku.
- Bestehende Vierarmfälle erhalten; gemeinsame Zeitparametrierung innerhalb
  des Zweierverbunds. Keine Dienstneustarts oder Trainingsläufe vorgesehen.
- Armzuordnung wird anhand der kurzen Objektseiten und Modell-Erreichbarkeit
  gewählt; Modellgeometrie und echte aktuelle Hardwarestellung nicht vermischen.
- Ergebnis: RF/RR aufx_min/x_max, linkeArmegeparkt. DreiakzeptierteBeispiele,
  zweikollidierendeReferenzenkorrigiert; einIK-Fehlerbleibtnegativ. Daten/Viewer:
  setup/research/two-arm-object-teacher-20261117/run02/.
- Objekt/Unterarmkollisionen auserstemOptimierungsversuch unabhängigmitFCL
  gefunden undalsSteuerungsbedingungen ergänzt. NegativeProben/Logs erhalten.
- Build,28Pythonprüfungen, alterVierarm-Verifier, unabhängigeGradienten/
  Endpunkt-/Zeitableitungs-/Negativkontrollen und80BrowserchecksPASS. Screenshot
  kontrolliert. Nachweis/Bedienung docs/two_arm_object_teacher.md undHANDOVER.
- KeineTrainings-/Hardware-/Kontaktphysikaktion. NurkleinerDemonstrationssatz,
  keineglobaleLehrer-/Sicherheitsqualifikation. Datengeneration alsFolgestufe.
