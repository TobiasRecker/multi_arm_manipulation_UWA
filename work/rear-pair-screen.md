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

## Kontakt im 3D-Viewer, 2026-11-18

- Abgeschlossen. Schritt 1 visualisiert die +60°-Referenz zwischen den hinteren
  Armen in der archivierten Szene. Der vorhandene HTML-Viewer zeigt die 17 von
  61 FCL-Kollisionspunkten und die beiden Unterarme. Startansicht bei 50 %.
- Pose, Gelenkzustand und Kollisionspaar des ursprünglichen Kontaktzeugen
  reproduziert. Die markierte Region ist aus den Kugelhüllen geschätzt. Zehn
  Browserprüfungen bestanden und die Startansicht visuell geprüft.
- Bedienung und Nachweis unter `contact-preview/` im Forschungsordner.
  Reproduktion über `tools/preview_rear_pair_collision.py SCREENING_ORDNER
  --output-dir NEUER_ORDNER` in der Zellumgebung.

## Korrektur durch den Lehrer, 2026-11-18

- Abgeschlossen. Bestehender Lehrer für dieselbe archivierte Referenz mit
  festen Endposen und Griffen. 1.201 geprüfte Wegpunkte mit null FCL-Kollisionen
  und mindestens 20,92 mm Armhüllabstand. Maximal 45,0 mm und 33,44° Korrektur.
- Reproduktion in der Zellumgebung mit `tools/plan_rear_pair_teacher.py
  SCREENING_ORDNER --output-dir NEUER_ORDNER`. `--candidate` prüft vorhandene
  Optimierergebnisse erneut. Resultat und Vergleichsviewer unter
  `teacher-step2/checked/`. Elf Browserprüfungen bestanden. Gemeinsames
  Zeitgesetz sowie Prüfung der zeitparametrierten Bahn folgen in Schritt 3.

## Fortsetzung zu einer eigenen Zielpose, 2026-11-18

- In Arbeit. Nutzer fragt nach dem Ziel nach der Ausweichbewegung. Archivierter
  Viewer und Pose bei 100 % geprüft. Ausgangsfall kehrt zur Startpose zurück.
  Gezielte Offlineprobe mit eigenem Ziel und freiem Wegstück nach dem Konflikt.
