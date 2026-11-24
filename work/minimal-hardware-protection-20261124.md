# Neuer minimaler Hardware-Schutz, 24.11.2026

- Status: Implementierung und Kandidatenprüfung abgeschlossen, 24.11.2026.
  Operative Aktivierung und reale Funktions-/Anhalteprüfung bleiben ein eigener
  Betriebswechsel. Hauptagent dieses Chats.
- Auftrag: beschlossenen C++-Kollisionskern und gemeinsame Arm-Pause mit
  ausdrücklicher Fortsetzung implementieren; Robot Power und Motion Review erhalten.
- Automatische Pause ausschließlich bei Geometriekonflikt. Fehlende Kollisionsdaten
  warnen nur. Greifer ausschließlich als Geometrie, keine Greifer-Schutzprüfungen.
- Bestehende 40-mm-Nachbararmmarge und sonstige FCL-Kontaktgrenzen erhalten.
  Keine zusätzliche Tischmarge und keine neue Geschwindigkeitsfreigabe.
- Bereiche: neues Paket uwa_cell_protection, Controller-Plugin, Ausführungsadapter,
  GUI/Bridge, getrennte Kandidatenwerkzeuge und Dokumentation. Vorhandene gestagte
  Motion-/Marker-/Dokumentationsänderungen bleiben erhalten.
- Keine echten Ziele, Power-/Brake-/Play-Aktionen oder Hardwaredienstneustarts.
  Keine Sicherheits-/Fehlertests in Gazebo. Softwareprüfung isoliert in Domain67.
- Nächster operativer Schritt: eigener Betriebswechsel auf den gebauten,
  bislang inaktiven Kandidaten; keine automatische Fahrt oder Aktivierung.

## Historischer Stand beim Pausieren

- Implementierung und Migration einschließlich Kamera-Library, Parking,
  Akquisitionsfolgen und Scan vorhanden; 157 gezielte Pythonprüfungen und
  alle sechs C++-/Controller-Mocktests bestanden.
- Hashgeprüfter inaktiver Kandidat auf N100:
  `/home/rosmatch/uwa-ur-runtime/minimal-candidates/minimal.upWhPwQC`.
  Lokale Quellen entsprechen dessen Manifest. Operative Runtime unverändert.
- Der niedrig priorisierte Build der fünf geänderten Pakete wurde gezielt
  mit SIGSTOP angehalten, einschließlich seiner Compiler-Unterprozesse.
  Build-Hauptprozess PID3365192; vollständige PID-Liste und Kandidatenbindung:
  `setup/tasks/minimal-protection-20261124/n100-build-paused.json` im Workspace.
  Nach Nutzerfortsetzung vor SIGCONT die jeweiligen Prozesse/Startidentitäten
  erneut diesem Kandidaten zuordnen, keine fremden Prozesse fortsetzen.
- Die damalige SSH-Wartesitzung73693 ist inzwischen erfolgreich beendet.
  Historische PIDs nicht erneut signalisieren; sie sind kein aktueller Auftrag.

## Fortsetzung

- Nutzer hebt die Pause ausdrücklich auf. Build-Hauptprozess und gespeicherte
  Kinder anhand Kandidaten-Arbeitsverzeichnis, colcon-Aufruf, Elternkette und
  Stoppzustand erneut zugeordnet; ausschließlich diese Prozesse mit SIGCONT
  fortgesetzt. Identitäten und Startwerte:
  `setup/tasks/minimal-protection-20261124/n100-build-resumed.json`.
- Getrennter N100-Build erfolgreich beendet; abschließender inkrementeller
  Build: fünf Pakete, Exit0. Quellenmanifest auf dem N100 vollständig geprüft.
- Schlussprüfung:168 Pythonprüfungen und6/6 C++-/Controller-Mocktests bestanden,
  einschließlich echter vier GenericSystem-Manager und zwei Aufgaben nacheinander.
- Karton-Library-Preflight und beide SCP-Ziele auf denselben konfigurierten
  Kandidaten gebunden; zusätzliche Regressionen bestanden. Colcon sucht nur
  unter `src`; `COLCON_IGNORE` isoliert den Kandidaten von fremden Workspace-Scans.
- Dateibasierter N100-Nachweis: JTC6.9.0, Controller Manager6.10.1; alle Bibliotheken
  von Plugin, Schutzknoten und Replay aufgelöst. Pythonmodule stammen aus dem
  Kandidaten. Kein Schutzknoten oder Hardwaretreiber für diese Prüfung gestartet.
- Fünf archivierte Zustände auf beiden Rechnern identisch entschieden; sämtliche
  verglichenen Nachbarabstände exakt gleich. Kanonische Geometrie-/Mesh- und SRDF-
  Bindungen gleich; rohe Modellhashes unterscheiden nur die Mesh-Dateipfade.
  N100:399ms Modellaufbau,12,1–27,0ms ungecachete und0,035–0,057ms identische
  gecachete Zustände in dieser kleinen Stichprobe. Kein Dauerlast-/Anhaltebeleg.
- Nachweise im Workspace `setup/tasks/minimal-protection-20261124/`:
  `python-complete-tests.log`, `cpp-final-ctest.log`, `n100-final-build.log`,
  `n100-validation/runtime-binding.json`, `n100-cross-host-parity.json`,
  `n100-final-source-sha256.txt`. Bedienung: `docs/minimal_hardware_protection.md`.
- Abschlussgrenze: operative Runtime durch diese Arbeit nicht geändert; keine
  realen Arm-/Greifer-/Power-/Brake-/Play-Befehle, keine Gazebo-Sicherheitstests.
