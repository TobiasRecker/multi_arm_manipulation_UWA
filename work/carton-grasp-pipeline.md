# Modulare Karton-Greifpipeline

- Status: **in Arbeit**, 2026-11-13, Hauptagent Greifpipeline.
- Auftrag: wiederverwendbare Skills/CLI/Reviews, zuerst Simulation mit beiden
  rechten URs, leerer Karton, physischer Kontakt, kurzer Hub und Absetzen.
- Nutzerentscheidung: Agent prüft und setzt im konkreten Auftrag selbst fort;
  keine zusätzlichen manuellen Freigaben je Phase. Hardware ist spätere Arbeit.
- Verbindlich: ab bestätigtem Griff starres Multirobotersystem; ausschließlich
  Objektpose/-twist vorgeben, feste Objekt→TCP-Transformationen. Keine unabhängig
  geplanten tragenden Arme. Prinzip/Kern aus match_cooperative_handling nutzen.
- Bereiche: neues uwa_cell_tasks, kontaktfähiges optionales Simulationsprofil,
  gemeinsamer geometrischer Kern im Cooperative-Repo, gezielte Integration und
  Tests/Anleitung. Bestehende Motion-/Tracking-Diffs erhalten.
- Gemeinsame Simulation: laufender Vierarmvergleich hat Vorrang; keine fremden
  Dienste stoppen/neustarten. Zunächst Offlinearbeit. Eigene Kontaktprüfungen
  getrennt benennen; Zellneustart erst nach tatsächlicher Nutzungsprüfung.
- Annahmen: starrer leerer Karton, 0,3kg, Reibwert0,6; ungemessen. Hub30mm,
  Halten2s, keine künstliche Objektbefestigung als Haltenachweis.
- Noch offen: Implementierung, Build, Software-/Kontaktprüfung und fünf volle
  Zellläufe. Nur tatsächlich ausgeführte Nachweise als bestanden dokumentieren.
