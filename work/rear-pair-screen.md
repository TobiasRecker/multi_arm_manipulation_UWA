# Hinteres Armpaar für Karton-Lehrer

- Status: Offline-Erstprüfung in Arbeit, 2026-11-17, Hauptagent dieses Chats.
- Nutzer schlägt hintere statt rechte Arme vor; vermutet zu wenige Kollisionen
  mit bisherigem Karton/Basenaufbau. Zunächst neue hypothetische Griffstarts
  und kleine Referenzstichprobe prüfen, keine Hardware-/Simulationsdienste.
- Bestehende ObjectTransport-/Teacher-/Mehrstart-IK/FCL-Bausteine wiederverwenden;
  starre Griffe, alle Fremdarme und unveränderte Kollisionsbedingungen erhalten.
- Eigene Untersuchungsquellen/Artefakte unter setup/research/rear-pair-screen-20261117/;
  keine Änderungen an laufenden Lehrer-/Hardwarekernen oder fremden Arbeiten.

## Abschluss

- Status: **Offline-Erstprüfung abgeschlossen**. Drei gültige Startlagen,
  je sechs ±60°-Weltachsen-Drehreferenzen/5cmZwischenhub. FCL-Fälle0/1/5,
  IK-Abbrüche2/1/0. Hintenste geprüfte Lage hat84,8mmArmhüllabstand am Start.
- Nativer Kontaktzeuge: linke/rechte hintere Unterarme bei+60°WeltZ.
  Keine erfolgreiche Kollisionsvermeidung oder sichere Anfahrt behauptet.
- Wiederverwendete Kinematik/Mehrstart-IK/Griffzwänge/FCL, keine produktiven
  Kernänderungen. Gleiche sechs Proben am rechten Kontrollstart ergeben
 1frei/5IK-Abbrüche; kleine gezielte Stichprobe, kein statistisches Ranking.
- result.json/summary.json/Kontaktlog und reproduzierbare Prüfscripte im obigen
  Ordner. Zeugenextraktionsfehler separat erhalten/korrigiert. Keine Geräte-,
  ROS-, Simulationsdienst- oder Fahraktion. Weitere Optimierung noch offen.
