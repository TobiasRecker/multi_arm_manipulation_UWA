# Kopierfertiger Testauftrag

```text
Erweitere unseren kooperativen Code-as-Policy-Piloten im Workspace
/home/rosmatch/UWA_ws. Lies zuerst
src/multi_arm_manipulation_UWA/docs/agent_trials/BOX_DRAWING_HANDOFF.md
und das dort verlinkte TRACE_PROTOCOL.md; beachte die geltenden AGENTS.md.

Zwei rechte Arme halten die Box, left_front zeichnet. Zusätzlich zu den
bisherigen Kreisen auf y_max und z_min soll die Box weitergedreht werden,
sodass derselbe Arbeitsarm auch auf der gegenüberliegenden Längswand y_min
einen Kreis mit 25 mm Radius ausführt. Erhalte die beiden bisherigen Kreise.
Wähle eine geeignete Haltepose und koordiniere freie Bewegungen sinnvoll.
Die Haltegruppe bleibt starr; der gesamte Hin-/Rückweg ist zu prüfen.
Es geht zunächst ausschließlich um die vorhandene kinematische Modellstufe.

Nutze die vorhandenen Bausteine, erweitere die nötigen Stellen und zeige
mir eine bedienbare Vorschau. Verwende für neue Modellläufe die aktuelle
Geschwindigkeitsvorgabe 0,1 rad/s. Erhalte Kollisions-/Griff-/Stiftprüfungen;
keine reale Hardware, Kamera oder laufenden Dienste ansprechen.
Erzeuge zuerst einen plausiblen Vorschlag und dann die gezielte Endprüfung.

Dokumentiere deine Entwicklung von Beginn an nach TRACE_PROTOCOL.md:
initialisiere den Logger so früh wie nach den geltenden Startregeln möglich
und kennzeichne vorherigen Kontextaufbau als unerfasst, sofern unbelegt.
gemessene Zeiten für Orientierung, Referenzprüfung, Anpassung, Planung,
Verifikation und Übergabe; Befehle, vollständige stdout/stderr, Exitcodes,
Fehlversuche/Reparaturen, Änderungen und Artefaktpfade. Andere Toolaktionen
und kurze Entscheidungen notieren. Erfinde keine Denkzeiten oder Tokenzahlen.
Speichere alles in einem neuen eigenen Trialordner unter
setup/agent_trials/box_away_face_20261118/ und protokolliere abschließend
Ergebnis, verbleibende Einschränkungen und die Wiederverwendung des Toolkits.

Liefere den Viewerpfad, die geprüften Ergebnisse sowie Trialordner und
report.md, damit der ursprüngliche Agent deinen Lauf auswerten kann.
Bewahre vorhandene Änderungen und Referenzläufe. Bei einem Hindernis
diagnostiziere es konkret und behalte negative Ergebnisse im Protokoll.
```
