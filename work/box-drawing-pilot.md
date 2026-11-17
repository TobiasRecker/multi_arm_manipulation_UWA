# Kooperativer Code-as-Policy-Pilot: Box halten und zeichnen

- Status: erster Feedbackzyklus abgeschlossen, 2026-11-17 (Australia/Perth), Codex dieses Chats.
- Neues echtes Nutzerfeedback zu run08: Umkonfiguration vor Unterseitenkreis
  hinterfragt; höher/näher am Arbeitsarm halten oder Wechsel während der
  Boxdrehung prüfen. Feedback an transfer_to_z_min speichern, Originalepisode
  erhalten; Ursache und Varianten mit identischen Modellprüfungen vergleichen.

- Ergebnis: Feedback gespeichert, neueProgramme mitParent-Episode/Feedbackhash
  gebunden. overlap01gleicheBoxpose/gleichzeitigerWechsel49,837s; closer01
  8cmnäher/kleineGelenkhübe68,073s inkl.Hin-/Zurückversetzen. Original66,858s.
  Initial-/Endwerteidentisch, zweiKreiseundGrenzengleich. Kein versteckter
  Vorteil durch geänderteStartfixture oder gelockertePrüfung.
- Beide Interpolantenmodellgeprüft undseparatFK/Zeit/EpisodenauditiertPASS;
  overlap2504/closer3421Prüfzustände, minHülle230,818/213,628mm.
  KontaktsimulationundHardwareweiteroffen. NäherePoseentferntgroßenWechsel,
  überlappendeReferenz reduziertZeit25,46%, keineglobaleOptimalitätbehauptet.
- 13SoftwaretestsPASS,35/39Browserchecks+7VergleichchecksPASS, Screenshots
  visuellgeprüft. Vergleichfeedback-comparison01/viewer.html. Quellbaum-CLI
  umVarianten/Feedbackbindung erweitert, eigenerVergleichrunner hinzugefügt.
- NegativeundpositiveProbes unterfeedback01erhalten. ErsteCloserprobeprüfte
  fälschlichdenaltenWorkerplatzvorderNeubelegungderInitialfixture undverwarf
  Boxverschiebungen; korrigierteSeparateprobeerhalten, keinUnlösbarkeitsbeweis.
- Nutzer bestätigt Pilotbeginn. Erste Auswertung bewusst anhand verfügbarer
  Ausführungsdaten: Dauer, Kraftmaximum mit Quelle/Abdeckung, Fehlgriff,
  Neuansatz, Objektverlust, Agentenintervention und subjektives Endfeedback.
  Keine aufwendige automatische Strichbild-/Produktoptimierung voraussetzen.
- Bereiche: neue getrennte Pilot-/Episodenmodule und CLI/Vorschau/Tests,
  Dokumentation; bestehende Task-/Teacher-/Hardwarequellen erhalten.
- Erstes Ziel: überprüfbares kooperatives Aufgabenprogramm, Modellvorführung,
  echte protokollierte Ereignisse/Feedback. Kinematische Vorführung und
  Kontaktphysik/Realnachweise ausdrücklich unterscheiden. Keine erfundenen
  Kraft-, Griff- oder Verlustmessungen aus geometrischen Animationen.
- Keine Hardware-/Kameraaktion oder Neustarts bestehender Dienste. Neue eigene
  Berechnungen getrennt unter setup/tasks/box_drawing_pilot_20261117/.
- Fremde aktive Teacher-Episoden/OAK-/Stopparbeit erhalten; gemeinsame
  Dokumente nur kleine ergänzende Änderungen. Kein neuer Teilagent.

## Ergebnis und Prüfung

- Neue Module pilot_episode.py/box_drawing.py, CLI box_drawing_pilot.py,
  separate Verifikation und kontrastreiche HTML-Vorschau. Gespeicherte
  Pythonpolicy tatsächlich gegen Modelladapter ausgeführt. Keine native
  Neuinstallation/Änderung laufender Taskwelten erforderlich.
- run08: zehnPhasen,66,858sModellzeit,3358Zustände≤20ms, FCL/alle6Paare/
  bewegterKarton/Markerkörper/GriffschlussPASS. ZweiFlächen y_max/z_min,
  fixeIn-air-Annahme, keineKontakt-/Kraft-/Griffmessungen. API speichert
  fehlendeBeobachter alsUNKNOWN undNutzermeldungen getrennt.
- NegativeLäufe1–5undProbes erhalten. run06/07erste vollständigeModelle;
  run08aktuelleUI-/Quellbindung. GefundeneRF/LF-BewegungennurModellnachweise.
- UnabhängigerFK-/Zeit-/EpisodenauditPASS,1510FK/2001AbleitungssamplesjePhase.
  13gezielteTestsPASS,39BrowserchecksPASS, preview.pngvisuellgeprüft. QA hat
  keinenBeispieltext alsNutzerfeedback gespeichert. Hostbrowserisoliert;
  sandboxedChromiumzunächstsetsockoptEPERM, danachHostprüfungPASS.
- Anleitung docs/box_drawing_pilot.md; AGENTS/HANDOVER/README und früheren
  Konzeptstand an Nutzerpräzisierung angepasst. Vorhandene fremde Diffs und
  bereits gestagte/zwischenzeitlich gespeicherte Arbeitsstände erhalten.
- NächsteIntegration: subjektivesFeedback, Kontakt-/Ausführungsdatenadapter,
  Teleopübernahme undCodeverbesserung mitRegressionen. AktuellerViewer ist
  eine Modellvorführung, keinefertigephysischeDreiarmausführung.
