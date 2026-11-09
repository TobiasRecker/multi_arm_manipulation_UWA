# Laufende Arbeiten und Zusammenarbeit

Seit 2026-11-09: Status pro Aufgabe in **`work/*.md`**, jeweils von ihrem
bearbeitenden Agenten gepflegt. Vor Änderungen alle aktiven Einträge lesen.
Die Dateien sind eine Absprachehilfe, keine technische Dateisperre.

Jeder Eintrag nennt Aufgabe/Agent, Status, letzte Aktualisierung in Australia/Perth,
betroffene Dateien oder Bereiche, nächste Schritte und geplante Dienstneustarts.
Zu Beginn anlegen, bei relevanten Änderungen aktualisieren, zum Abschluss auf
`abgeschlossen` setzen und die dauerhaften Ergebnisse nach `HANDOVER.md` übertragen.
Fremde Einträge nicht stillschweigend schließen oder überschreiben.

Bei Überschneidungen Änderungen klein und bereichsweise anwenden und vorher
den aktuellen Diff erneut lesen. Für umfangreiche parallele Änderungen an
denselben Dateien sind getrennte Git-Worktrees mit anschließender Integration
vorzuziehen. Der installierte Simulationsdienst bleibt eine gemeinsame Ressource:
Neustarts hier ankündigen; gleichzeitige Bewegungsprüfungen vermeiden.

Einträge finden: `rg --files work -g '*.md'`. Neue Agenten tragen sich selbst
ein; diese Datei muss dafür nicht jedes Mal geändert werden.
