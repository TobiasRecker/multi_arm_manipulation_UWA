# Erste Tagesinbetriebnahme: irreführende Sicherheitsbestätigung

- Status: ausdrücklich genehmigte Startkorrektur umgesetzt und auf N100
  installiert,25.11.2026. Hauptagent dieses Chats.
- Nutzerfreigabe: „ja bitte :)“ zur konkret beschriebenen Korrektur einschließlich
  zusätzlicher Statusabfragen ausschließlich während des nativen Ladeübergangs.
- Nutzerbeobachtung: beim ersten Tagesstart meldet Robot Power eine Prüfung
  der Sicherheitskonfiguration am Pendant; dort keine Änderung oder Popup.
- Bereiche: begrenzte Änderung an `ur_bringup.py`, sachlicher GUI-Text,
  Offline-Regression und Installation der beiden Skripte auf ihren Bedienhosts.
  Keine Power-/Brake-/Load-/Play-/Resume- oder Bewegungsbefehle für diese Arbeit.
  Keine N100-Schutz-/Treiberneustarts; lokale GUI nur im bestätigten Leerlauf neu laden.
- Bestehende parallele Stift-/Wiegearbeiten erhalten. Keine Änderung am
  C++-Kern, Controller oder normalen Bewegungspfad.

## Konkreter heutiger Ablauf

Quelle: Workspace `setup/logs/uwa-control/sessions/20261125_151706_50406_6a0707fe/gui.log`.
Zeitangaben Australia/Perth; gespeicherte Ereignisse sind UTC.

- 15:17:07: left_rear und right_rear POWER_OFF/NORMAL,
  `/programs/<unnamed>.urp`. Beide vorderen Arme hatten `ros.urp` schon geladen.
- 15:17:20,779 left_rear: `load ros.urp` antwortet erfolgreich mit
  `/programs/ros.urp, /programs/tobias.installation`. Anschließender Snapshot:
  `mode=CONFIRM_SAFETY`, `safety=NORMAL`, Programm STOPPED; Ergebnis
  `confirm_safety`. Kein Power-/Brake-/Play-Befehl für diesen Arm im ersten Aufruf.
- 15:17:29,515 right_rear: derselbe Ablauf und dieselbe Zustandskombination.
- 15:17:32,181: beide hinteren Arme wieder POWER_OFF/NORMAL, nun `ros.urp`
  geladen. Die kurzen CONFIRM_SAFETY-Snapshots waren somit keine dauerhaften
  aktuellen Zustände. Eine Konfigurationsänderung ist dadurch nicht belegt.
- 15:17:38 zweiter Start: kein erneutes Laden; reguläres Power/Brake/Play.
  Alle vier Arme bis15:18:13 ROS-ready. Nutzer berichtet keine Pendant-Popup-
  Bestätigung; aus dem Log allein keine lückenlose Pendant-Bedienhistorie ableiten.
- Das Auftreten passt zum ersten Laden nach dem Einschalten. Ein täglicher
  Timer oder periodischer UWA-Prüfzwang existiert in diesem Meldungspfad nicht.

## Ursache und Einordnung

`ur_bringup.py::wait_for()` ruft nach dem Laden zuerst `safety_check()` auf.
Dieses deutet jeden Snapshot CONFIRM_SAFETY unmittelbar als notwendige manuelle
Sicherheitsbestätigung und bricht ab, bevor es den nächsten regulären Zustand
abwarten kann. `ur_cell_power.py::status()` verwendet dieselbe Kategorie.
`ur_power_gui.py::GUIDANCE` zeigt dazu pauschal den Pendant-Hinweis. Fehlgeschlagene
Aktionen können zusätzlich als `Last action` sichtbar bleiben, obwohl der
aktuelle Zustand bereits weitergegangen ist.

Der Auslöser ist ein tatsächlich gelesener nativer Robotermodus; die kategorische
Interpretation als manuell nötige Konfigurationsprüfung ist bei dieser heutigen
kurzen Ladephase zu stark. Robotermodus und nativer Sicherheitsstatus sind getrennt.
Die aktuelle UR-Dokumentation beschreibt CONFIRM_SAFETY als Validieren/Aktualisieren
der Sicherheitseinstellungen (ausführliche Definition ab5.25/10.12; kein pauschaler
versionsgenauer Coldboot-Nachweis für ältere Firmware). Eine tatsächlich beim
Installationsladen erforderliche Safety-Bestätigung ist für Dashboard als
Ladefehler dokumentiert. Im vorliegenden Log war die Ladeantwort erfolgreich.

Primärquellen, gelesen25.11.2026:

- [UR RTDE Robot Mode](https://docs.universal-robots.com/tutorials/communication-protocol-tutorials/rtde-guide.html#robot-mode)
- [UR Dashboard load/robotmode/safetystatus](https://www.universal-robots.com/manuals/EN/HTML/SW5_25/Content/prod-dashboard/Dashboard_table.htm)

## Konkret genehmigte Änderung

Nach eigenem erfolgreich bestätigtem Programmladen die Kombination
CONFIRM_SAFETY/NORMAL als noch laufenden nativen Ladeübergang behandeln.
Im bereits vorhandenen Startzeitfenster bis30s mit bestehendem250-ms-Abstand
weiter lesen und sofort fortfahren, sobald der native Modus wieder regulär ist.
Keine feste Zusatzwartezeit. Dauerhafte oder echte native Sperren weiterhin
konkret melden; keine Bestätigung, Sicherheitsänderung oder Befehlswiederholung
auslösen. GUI-Text zum tatsächlichen Zustand passend formulieren.

Mögliche Kosten: zusätzliche Dashboard-Abfragen und Wartezeit ausschließlich bei
diesem Startübergang. Laufende Trajektorien erhalten dadurch keinen weiteren
Prüfpfad. Wegen der ausdrücklich verlangten Vorabfreigabe für mögliche
Performancekosten war die konkrete Zustimmung erforderlich und liegt nun vor.

## Umsetzung, Prüfung und Installation

- `ur_bringup.py::wait_for`: ausschließlich beim eigenen erfolgreichen
  `load` wird CONFIRM_SAFETY/NORMAL im vorhandenen Ladefenster abgewartet.
  Bei anhaltendem Zustand endet es weiterhin mit `confirm_safety`. Andere
  native Fehler bleiben sofort wirksam; auch bei CONFIRM_SAFETY werden
  nicht-normale Sicherheitsfehler konkret gemeldet. REDUCED erhält keine
  neue Warteausnahme. Andere Startphasen bleiben ohne diese Ausnahme.
- Kein fixes Zusatzsleep im normalen Ladefall; kein erneuter Load-/Power-/
  Brake-/Play-Befehl durch die Korrektur. Lokale/andere Programmzustände
  werden auch während des begrenzten Wartens weiter korrekt behandelt.
- Englischsprachiger GUI-Text jetzt sachlich:
  `Controller reports CONFIRM_SAFETY. If it persists, check the safety message at the Teach Pendant.`
  Keine neue Abfrage, kein Timer und keine Änderung an der Aktionshistorie.
-50 gezielte Prüfungen bestanden:30 bestehende Start-/Standbytests gegen
  lokale Dashboard-Doubles,19 neue In-memory-/Fakeclock-Tests und ein
  GUI-Texttest. Normaler Kaltstart samt transientem Modus läuft im Double
  mit exakt je einem load/power/brake/play durch. Dauerhafter Modus verhindert
  Power/Play; ursprünglicher regulärer Ladefall benötigt keinen weiteren Sleep.
  Python-Kompilierung und Diffprüfung bestanden.
- Die anfänglichen Loopbacktests konnten in der Dateisandbox keine lokalen
  TCP-Sockets öffnen. Der anschließende Lauf mit erlaubten lokalen Sockets
  bestand vollständig; keine physischen URs an diesen Tests beteiligt.
- Auf N100 ausschließlich das Startskript im aktiven Kandidaten atomar ersetzt.
  Vorher `803aa86e81977297c3fa4f268d635d81277ce3b0e325e88ab7b768d42de49483`,
  installiert `4cfa159e3a9439851c5d60202f8140727322e220f1d89eac5ecaa38c7e69d0cd`.
  Nur dessen Eintrag in `SOURCE_SHA256SUMS` aktualisiert, übrige Einträge erhalten.
  Rücksicherung im Kandidaten:
  `validation/first-start-confirm-safety-20261125.t18lm8qd/`.
- Tatsächlich installierte Datei auf N100 importiert und mit vier künstlichen
  Fällen geprüft: transient, regulär ohne Wartezeit, dauerhaft, native Sperre.
  Dafür keine Sockets/ROS/Roboterbefehle und keine Dienstneustarts.
- Laufende lokale GUI PID50406 eindeutig auf Minimal-Kandidat gebunden.
  Noch offene Stift-Bewegungsfreigabe `743ee5361d9944d79515d9d588c19246`
  erhalten; GUI deshalb nicht neu gestartet. Backendkorrektur wird beim nächsten
  Startaufruf frisch geladen. Der statische neue Hinweistext erscheint nach
  dem nächsten normalen Öffnen der GUI.
- Kein künstlicher realer Kaltstart, keine Reload-/Power-/Bewegungsaktion
  für die Prüfung. Beobachtung beim nächsten regulären Kaltstart steht aus;
  Softwareprüfung und Installation sind abgeschlossen.

Nachweise im Workspace `setup/tasks/ur-first-start-confirm-safety-20261125/`:
`evidence.json`, `existing-start-tests-loopback.log`, `transition-tests.log`,
`gui-text-test.log`, `pre-install-review-and-manifest.txt`, `installation.json`,
`verify_installed_start.py` und `installed-file-verification.json`.
