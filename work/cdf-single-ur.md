# CDF für einen UR mit eingefrorener Restzelle

- Status: **abgeschlossen – erster Offline-/Simulationsprototyp**,
  2026-11-16 (Australia/Perth), Hauptagent CDF.
- Nutzer beauftragt ersten Nachbau des CDF-Paperansatzes für einen bewegten UR;
  drei andere URs zunächst starre Kollisionsobjekte. Originalprojekt/Code lesen,
  Nichtparametrisches CDF und darauf aufbauende Planung zuerst offline/Simulation.
- Bereiche: neue CDF-Module/CLI/Tests im Paket uwa_cell_motion, eigene Artefakte
  unter setup/research/ und setup/logs/, Anleitung, AGENTS/HANDOVER/README.
  Gemeinsame volle MoveIt-Endprüfung/Wächter erhalten, keine reale Fahrt.
- Parallele Greifpipeline und Power-GUI unverändert lassen. Kein Neustart einer
  gemeinsamen Simulation, kein realer Treiber-/Kamera-/Programmbefehl geplant.
- Originalcode gelesen: MIT, Commit08a725718e748366c5b4da5cbc4c67e991961f0f.
  Implementiert wird die nichtparametrische szenenbezogene Variante aus
  AbschnittIII/2D-online-Beispiel; kein Franka-Netz auf UR anwenden. Sphere-/
  Box-SDF nur zur Kontaktdatenerzeugung, CDF selbst Norm in Gelenkradian mit
  Präfixgradient, darauf Paper-QP mit logarithmischer Abstandsbedingung.
- Erster blockierter RR-Fall PASS:63Kontaktzustände/1024Seeds,18,26s Vorbereitung,
 0,585s Onlineplanung/3,218s einschließlich gemeinsamer Endprüfung. Vollständiger
  feststehender Restzustand erhalten. Erster Nachweis setup/research/cdf-ur-v1/.
- Final17CDF-Tests/107Paketchecks PASS, darunter Batch-FK aller4URs, analytische
  SDF-/CDF-Gradienten, Modell-/Tool-/Fremdarmbindung, unabhängiges QP-Optimum
  und Fremdarmstillstand. Logs setup/logs/uwa-cdf-{build,all-tests}.log.
-27Offlineversuche:3Aufgaben×3Seeds×3Planer, alle6gültigen Wiederholungen je
  Verfahren bestanden, je3unzulässige Ziele korrekt abgelehnt. Nur2gültige
  Aufgaben, keine repräsentative Erfolgsstatistik. Bericht/Plot/Modellanimation
  setup/research/cdf-ur-comparison-v2/. Kontaktbankkosten getrennt ausgewiesen.
- v1 mit2numerischen SLSQP-Falschabbrüchen erhalten; v2 löst exakt denselben QP
  direkt über skalaren Dual und benutzt identische Kontaktbanken. Blockierter
  Fall danach3/3PASS, CDF-Bedingung beeinflusst5–6Schritte. Kein RRT-Fallback.
- Wissenschaftliche Grafik visuell geprüft; Play/Pause/Slider/Reset/Zoom und
  endliche Projektion in JS-VM bestanden. Browserhost für realen GUI-Check
  nicht verfügbar, nicht als Browserprüfung ausgeben. HTTP-Testserver beendet.
- Anleitung/Attribution/AGENTS/HANDOVER/README gepflegt. Keine Gazebo- oder
  reale Ausführung, kein Dauerdienst/Neustart. Nächste separate Forschung:
  größere Suite, Projektionsfehler/Abdeckung, Physikreplay, ggf.neuronales UR-CDF.
- Installierte Query/Plan/Preview-Befehle end-to-end PASS:
  setup/research/cdf-cli-smoke/, setup/logs/uwa-cdf-cli-smoke.log. Blockierter
  CDF-Plan gültig/6beeinflussteQP-Schritte; einzelne Beispielprojektion mit
 0,566µm Rest zum eigenen vereinfachten Modell, keine Genauigkeitsstatistik.
