# Stiftlauf: Approved, aber erste Trajektorie abgewiesen

Nutzer fragt25.11., warum nach Approved keine Bewegung erfolgte. Betroffen:
Library-Lauf `52befffcfa974f6390b4658d081ae7d4`, Review
`b0d81aa4580b48b0b8cc4a38e6e1ce1a`.

## Nachvollzogener Ablauf (AWST)

-16:34:56,334 GUI: Reviewstatus approved;16:34:57 running.
-16:35:38,148 GUI: Nutzeraktion `resume_all`.
-16:35:38,180 gemeinsame Rückmeldung RUNNING, Generation534626124708923,
  aber Controllerbestätigungen noch fehlend. Enthaltene left_rear-Quittung
  gehört noch zu534626124708922: paused=true, factor0, confirmed=false.
-16:35:38,215 links vorne bereits bestätigt; links hinten noch nicht.
-16:35:38,315 alle vier Resume-Quittungen bestätigt.
-16:35:39,116 GUI meldet Review failed: `left_rear: trajectory rejected`.
  Library-Rückmeldung/Download abgeschlossen16:35:43,261.

Workflow `APPROACH_FAILED`, ein nicht erfolgreicher erster Fahrversuch,
keine Greiferbefehle/Einfahrt/Kontaktphase. Der direkte ROS-Log des linken
Controllers enthält keine Basismeldung „Received new action goal“ für diesen
Versuch. Native aktuelle Abfrage RUNNING/NORMAL, `ros.urp` läuft. Gemeinsamer
Status aktuell RUNNING/OPERATOR RESUME, bestätigte Controller, keine Kollision.
Tatsächliche Gelenkgeschwindigkeit beim abgewiesenen Ziel nicht separat
gemessen; nicht aus geplanter0,1rad/s-Grenze als Istwert ableiten.

## Ursache und Grenzen des Nachweises

Minimal-Client `wait_unpaused()` berücksichtigt das gemeinsame paused-Flag.
Der vorhandene Controller weist neue normale Ziele jedoch zusätzlich ab,
solange seine lokale Pause aktiv oder seine Freigaberampe noch nicht auf1
ist (`pausable_jtc.cpp::rejects_new_motion`). Die globale Resume-Antwort kann
vor diesen lokalen Bestätigungen eintreffen. Der Stiftlauf sendete in dieses
Übergangsfenster. Zeitfolge, Quellen und fehlender Eintritt in den Basis-
Goalcallback grenzen den Fehler auf die lokale Zulassung vor Ausführung ein;
welcher der beiden lokalen Werte beim Callback genau noch sperrte, ist nicht
als Einzelprobe protokolliert. Kein Fehler der angenommenen Bedienerfreigabe
und kein neues Kameraposen-/Greiferproblem belegt.

Die offizielle ros2_controllers-Implementierung protokolliert den Eintritt
in den regulären Goalcallback vor dessen Validierung; unterstützend geprüft:
https://github.com/ros-controls/ros2_controllers/blob/master/joint_trajectory_controller/src/joint_trajectory_controller.cpp
Die konkrete Zulassungslogik stammt aus dem vorhandenen lokalen UWA-Controller.

## Aufgabenbezogene Korrektur

Nur Stift-Ausführungshelfer und Runner geändert; **keine Änderungen** am
C++-Schutzprogramm, pausable-JTC, gemeinsamen Minimaladapter, seinen
Befehlen, Fristen oder Grenzwerten.

Vor jedem nächsten Armkommando wartet der Stifthelfer anhand der bereits
abonnierten Statusdaten auf die vorhandene lokale Zulassung: gemeinsame
Pause aufgehoben, left_rear bestätigt dieselbe Generation, lokale Pause
aufgehoben und Faktor1. Keine zusätzlichen RPCs/Abonnenten/Managerabfragen,
keine Geschwindigkeits-/Stillstands-/Kraftwächter, kein automatisches Resume
oder Wiederholen eines abgewiesenen Ziels. Bei schon vollständig freigegebenem
Controller entsteht keine zusätzliche Warteschleife. Die Trajektorien und
ihre Geschwindigkeiten bleiben unverändert.

Aufgabenstatus `WAITING_CONTROLLER_RESUME` und deutlicher englischer
Laufhinweis zeigen diesen Übergang. Keine erneute Motion-review-Anforderung
aus dieser Meldung. Letzten Controllerstatus vor Dispatch/bei Fehler sichern.
29 gezielte Offline-Tests bestanden, einschließlich alter Generation trotz
globalem RUNNING, noch laufender Rampe, vollständig freigegebenem Zustand
ohne Wartezyklus und korrekter Fortschrittsanzeige. Kein Hardware-Fehlertest.

## Weiterer Versuch

Weiterhin beauftragte Stiftaufnahme mit frischen Eingaben neu vorbereitet,
Lauf `060e937a67c346d2b04263e86998a365`, Start16:42:36AWST über aktive
Library. Keine Wiederverwendung einer alten Freigabe oder automatische
Wiederholung des abgewiesenen Ziels. Neue normale Bewegungs-/Kontaktreviews
gehören zum Lauf. Keine Power-/Brake-/Play-/Pause-/Resume-Befehle durch diese
Diagnose; bestehendes vom Nutzer ausgelöstes Resume bleibt erhalten.

Neuer Plan18,406674s, weiterhin lokaler linker Boardbezug. Review
`0d0d013960714d27b08f67239c3be286` wartet auf Bedienung. Ein frischer
Statusaufruf verpasste zunächst die ROS-Serviceverfügbarkeit; einmalige
rein lesende Gegenprüfung: Dienst active/running, Invocation
`deff1ec32133419aac9e43114c55a84d`, left_rear bestätigt aktuelle Generation,
paused=false/Faktor1, Gesamtzustand RUNNING. Kein Dienstwechsel ausgeführt.
Nutzer um nur die neue Motion-Freigabe gebeten; erneutes Resume ist für
diesen bereits freigegebenen Zustand nicht erforderlich. Kontakt erst
nach neuer Einfahrbildprüfung. Kein zweiter Lauf parallel starten.

Nachweise unter `setup/tasks/pen-debug-20261125/`:
`resume-race-gui-events.json`, `approved-no-motion-status.txt`,
`trajectory-rejected-controller-log.txt`,
`trajectory-rejected-native-and-log-paths.txt`,
`resume-admission-regression.log`, `resume-fixed-live-run.json`.
