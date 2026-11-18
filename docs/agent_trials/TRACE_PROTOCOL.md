# Agentenentwicklung messen und zurückgeben

Standardlib-Logger: `tools/agent_trial.py`. Er misst **Agentenentwicklung**,
nicht Roboterzyklen. Python3 genügt; kein Build, ROS-Start oder Plugin nötig.
Das folgende Beispiel gilt aus einer Shell; bei frischen Shells die Variablen
erneut setzen. Einen neuen Trialnamen wählen, vorhandene Läufe erhalten.

```bash
WS=/home/rosmatch/UWA_ws
REPO="$WS/src/multi_arm_manipulation_UWA"
TRACE="$REPO/tools/agent_trial.py"
TRIAL="$WS/setup/agent_trials/box_away_face_20261118/trial01"
python3 "$TRACE" --trial "$TRIAL" init --repo "$REPO" --task box-away-face
python3 "$TRACE" --trial "$TRIAL" start orient
python3 "$TRACE" --trial "$TRIAL" run --label status -- git -C "$REPO" status --short
python3 "$TRACE" --trial "$TRIAL" end --note 'Regeln und Einstiegspunkte gelesen'
```

`init` legt den Trialordner an; ihn nicht vorher selbst erzeugen.
Optional `--agent` nur mit tatsächlich bekanntem Modell/Client ergänzen.
Git-HEAD und ursprünglicher Dirty-Status werden gespeichert; kein Commit/Reset.
Vorhandene kurze Übergabedateien und zentrale Pilot-/Loggerquellen werden
mit Hashes unter `context/` gesichert, damit der tatsächliche Eingang später
trotz Weiterentwicklung des Toolkits nachvollziehbar bleibt.
So früh wie nach den geltenden Startregeln möglich initialisieren. Zeit vor
`init` ist nicht gemessen; früheren Kontextaufbau nur mit vorhandenen
Clientzeitstempeln ergänzen, sonst als unerfasst kennzeichnen.

## Während der Arbeit

Stufen: `orient`, `baseline`, `adapt`, `plan`, `verify`, `deliver`.
Bei Rückkehr eine neue ID wie `plan02` verwenden, alte Stufen nicht umschreiben.
Vor einer Stufe `start NAME`, danach `end --outcome done|failed|blocked`.
Parallelbefehle innerhalb derselben Stufe sind möglich, Stufen nicht schachteln.

Shellbefehle möglichst über `run --label NAME -- COMMAND ARG...` ausführen.
Es wird keine Shell implizit gestartet. Für ROS-Umgebung und komplexe Befehle:

```bash
python3 "$TRACE" --trial "$TRIAL" start plan
python3 "$TRACE" --trial "$TRIAL" run --label candidate01 --timeout 900 \
  --cwd "$WS" -- bash -lc \
  'source src/multi_arm_manipulation_UWA/scripts/env.bash; OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 src/multi_arm_manipulation_UWA/tools/box_drawing_pilot.py --help'
python3 "$TRACE" --trial "$TRIAL" end --outcome done
```

Das Beispiel zeigt nur die Aufrufform; es ist kein Auftrag, zusätzlich einen
unveränderten Zweiflächenlauf auszuführen. `run` übernimmt den Exitcode des
Kindprozesses;0 bedeutet nur Befehlsabschluss. Timeout liefert124,
Startfehler127. Bei Timeout werden ausschließlich eigene gestartete Prozesse
dieses Befehls beendet. Keine Hintergrunddienste/Robotertreiber hier starten.
Vollständige Rohtexte bleiben erhalten; die Konsole zeigt nur deren Ende.

### Skripte und Patches über Standardeingabe

Bei `python3 -`, `bash -s` oder `apply_patch` genügt argv allein nicht zur
Reproduktion. Seit der Gegenwand-Auswertung vom18.11. erfasst `run` mit
`--stdin-file DATEI` die exakten Eingabebytes in `commands/…/stdin.bin`
und protokolliert Größe und SHA256. Der Kindprozess liest diese archivierte
Kopie. Dateipfade beziehen sich auf das Aufrufverzeichnis des Loggers.
`--stdin-file -` nimmt stattdessen die Standardeingabe des Loggers bis EOF:

```bash
python3 "$TRACE" --trial "$TRIAL" run --label edit-face --stdin-file - -- python3 - <<'PY'
print('Hier steht das tatsächliche Bearbeitungsskript.')
PY
```

Ohne diese Option bleibt die Standardeingabe vererbt und **unerfasst**;
neue Befehlsmetadaten nennen dies ausdrücklich `inherited_unrecorded`.
Die Option nur für aufgabenbezogene Skripte/Patches verwenden, keine
Passwörter oder Zugangsdaten aufnehmen. Bisherige Trials werden nicht
nachträglich vervollständigt. Externe Editor-/API-Aktionen weiterhin als
Notiz mit Diff bzw. sichtbarem Export ergänzen.

Bearbeitungen über apply_patch, Browser-/Bildtools und sonstige nicht gewrappte
Aktionen direkt in der aktiven Stufe vermerken, mit sichtbarer Fehlermeldung,
Dateipfad oder Toolreferenz. Nur kurze Entscheidungsbegründungen, keine
vermeintlich rekonstruierten internen Gedankengänge:

```bash
python3 "$TRACE" --trial "$TRIAL" note --kind edit \
  --text 'Flächenabbildung in Modell und Audit für y_min erweitert'
python3 "$TRACE" --trial "$TRIAL" note --kind error \
  --text 'candidate01: IK-Fortsetzung bei ... gescheitert; Log und Zustand ...'
python3 "$TRACE" --trial "$TRIAL" note --kind artifact \
  --text 'Vorschau und Bericht' --artifact "$TRIAL/artifacts/run01/viewer.html"
```

Fehlversuche nicht löschen oder durch erfolgreiche Ausgaben überschreiben.
Nutzerwartezeit bei Bedarf als eigene Stufe `user_wait01` ausweisen.
Keine Zugangsdaten oder komplette Umgebungsvariablen in Protokolle ausgeben.

## Abschluss und Rückgabe

```bash
python3 "$TRACE" --trial "$TRIAL" finish --status complete \
  --summary 'Dritte Fläche implementiert; Prüfungen/Viewer siehe report.md'
```

`failed`/`blocked` verwenden, wenn erforderlich; vorher offene Stufe beenden.
`summary` kann jederzeit Zwischenstände erzeugen. Erst nach der eigentlichen
Arbeit abschließen; Fehler werden nicht aus der Statistik entfernt.

Zurückgeben: **den gesamten Trialordner** und ggf. sichtbaren Chat-/Tool-Export
des Clients. Der Logger erfasst nur seine Befehle und explizite Notizen,
nicht automatisch sämtliche Agenten-API-/Browser-/Editor-/Chatausgaben.
Solche Ausgaben als Dateien/Notizen ergänzen; fehlenden Export kenntlich machen.

Der Ordner enthält `trial.json`, `events.jsonl`, `summary.json`, `summary.md`,
`commands/*/{command,result}.json` und vollständige stdout/stderr-Dateien.
Artefakte und Tests unter `artifacts/` ablegen. Zusätzlich ein kurzes
**report.md** schreiben: Ergebnisstatus und Viewer, verwendete Module,
geänderte Dateien, aufgetretene Fehler und Reparaturen, manuelle Hilfen,
konkrete Harnesslücken sowie noch unbekannte Messgrößen. Relevanten eigenen
Diff und finalen Quellstand/Hashes referenzieren; fremde Diffs nicht zuordnen.
In gemeinsam genutzten Checkouts Git-HEAD am Ende mit dem in `trial.json`
vergleichen. Bei parallelen Commits den eigenen Diff gegen die ursprüngliche
Revision **und** die Eingangssnapshots prüfen. Bericht, Diff und Prüfnachweise
vor `finish` abschließen; spätere notwendige Korrekturen separat datieren
und deren Zeit nicht der abgeschlossenen Messung zuschlagen.

Die Zeitentabelle enthält Stufenwandzeit und die Vereinigung aktiver
Befehlsintervalle; parallele Aufrufe werden nicht doppelt gezählt. Die
Restzeit umfasst Lesen, Bearbeiten, Chat und Warten. Sie ist **keine exakt
gemessene Denkzeit**. Token-/Modellkosten bleiben unbekannt, sofern der
Client keine belegten Nutzungswerte liefert. Roboter-Modellzeit weiterhin
separat aus der jeweiligen Episode berichten.
