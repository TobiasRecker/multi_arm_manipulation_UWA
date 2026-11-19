Du bist der frische Agent für den zweiten UWA-Kompatibilitätstest. Öffne
zuerst `docs/agent_trials/GEMINI_HANDOFF.md` und folge dem Einstieg dort.

Zwei rechte Arme halten den Avocadokarton. Der linke vordere Arm zeichnet
zuerst auf die zugewandte Längswand, dann auf die Unterseite und schließlich
auf die gegenüberliegende Längswand je einen Kreis mit **22 mm Radius**.
Der linke hintere Arm bleibt geparkt. Am Ende kehren alle Arme in die
Ausgangsstellung zurück. Erzeuge einen neuen Lauf im Offline-Kinematikmodell
mit der vorhandenen Toolchain und der geltenden Grenze von 0,1 rad/s.

Verwende das bereitgestellte Toolkit. Schreibe Ergebnisse in den eigenen
Trial-Ordner. Wenn ein Baustein fehlt, dokumentiere die Lücke und die
Fehlermeldung. Die Testumgebung umfasst gespeicherte Modelldaten und die
vorhandene Offline-CLI. Gazebo, Gerätekontakte und Dienste gehören nicht
zum Lauf. Änderungen am gemeinsamen Quellcode sind außerhalb dieses Tests.

Liefere Viewer, Modellergebnis, unabhängigen FK-/Zeitaudit und
`report.md`. Erkläre im Bericht in zwei bis drei Sätzen, welche Geometrie
der Viewer für die Haltearme zeigt und welche Daten für den tatsächlichen
Padabstand zur Kartonwand nötig wären. Übernimm keinen pauschalen
Höhenkorrekturwert in die Bahn.

Erfasse Entwicklungsschritte, Ausgaben, Fehler und Hilfen mit
`tools/agent_trial.py`. Schließe das Protokoll erst nach dem Bericht ab.
