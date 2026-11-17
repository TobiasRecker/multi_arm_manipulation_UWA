# Offline-Zielkandidaten und Plan-PDF

- Status: abgeschlossen - erste Offline-Kandidatenstufe, 2026-11-17
  (Australia/Perth), Hauptagent.
- Auftrag: Plan als PDF festhalten und ersten Schritt umsetzen. Interpretation:
  mehrere Zielkonfigurationen pro UR, statt bereits Zeitkoordination umzusetzen.
- Bereiche: neues isoliertes candidates-Modul/CLI im Motionpaket, gezielte Tests,
  Bedienungsdoku, output/pdf, AGENTS/HANDOVER. Bestehende Planer unverändert.
- Keine ROS-Knoten, Dienste oder Hardwareaktionen. Keine parallelen Taskquellen
  ändern. Vollständiges Modell nur offline über vorhandenen Problem-Loader.
- PDF: drei A4-Seiten gerendert und visuell geprüft.
- Ergebnisse: installierte CLI,13neueTestsPASS, zwei Vierarmdemos mit je8
  Kandidaten/Arm und16modellgültigen Kombinationen.64Posen/32Endstellungen
  unabhängig nachgerechnet; Budget-/Modellbindung und nichtausführbarer Status.
- Paketregression:125/126Pythonfälle im SandboxlaufPASS; ein bestehender
  Loopback-Sockettest außerhalb Sandbox einzelnPASS. NativeVorfilterprüfungPASS.
- Gemeinsamer Layoutwechsel durch Parallelauftrag erkannt und erhalten;
  ursprüngliche90cm-Demos separat eingefroren. Keine Hardware-/Dienstaktion.
- Anleitung docs/offline_goal_candidates.md, dauerhafte Ergebnisse HANDOVER.
- Folgeauftrag17.11.: Ergebnis anschaulich zeigen und Markdown-Vorschau erklären.
  Eigener Offline-HTML-Viewer mit auswählbaren Endstellungen; keine interpolierte
  Bewegung als geprüfte Bahn darstellen. Nur tools-/HTML-/Dokumentationsbereich.
- Viewer abgeschlossen, visuell geprüft und im Browser geöffnet.48Ansichten
  samt Moduswechsel/Status im echten Headless-Chrome geprüft. Reproduzierbarer
  Export aus gespeicherter URDF und Kandidaten, keine ROS-/Roboteraktion.
