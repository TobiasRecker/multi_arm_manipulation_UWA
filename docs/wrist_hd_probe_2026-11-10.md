# Praktischer HD-Modultest

Geprüft2026-11-10,20:16–20:18 Australia/Perth, right_rear192.168.8.170.
Nutzer gibt das Kamerazeitfenster ausdrücklich frei; paralleler Agent arbeitet
laut Nutzer an Bahnplanung. Keine Roboterbefehle oder Änderungen daran.

## Ergebnis

**Noch kein natives HD-/5MP-Foto erhalten.** Das temporäre Kameramodul lässt
sich anlegen, die Verarbeitung wird aber mit`code49156`,
`barcode process failed`, `status:failed` beantwortet. Ein separat gelesener
Barcode-Lizenzstatus meldet`licenseAvailable:true`; fehlende Freischaltung
ist damit nicht als Ursache belegt.

Das anschließende Modulbild ist640×480. Das zugehörige
`/map?type=scaletosource&x=640&y=480` liefert640/480. Dies bestätigt nur die
sichtbare Anzeigequelle; es beweist weder einen gültigen internenHD-Puffer
noch grundsätzlich dessen Abwesenheit. Ohne unabhängige Bestätigung hat der
Test den früher problematischen nativen Export nicht erneut aufgerufen.

Die Fehlermeldung ist generisch. Statische Analyse zeigt HD-Aufnahme vor
Barcode-Erkennung, aber der Status allein trennt Aufnahmefehler,
Modulvorbedingungen und fehlenden Barcode nicht zuverlässig. Keinen dieser
Gründe als bewiesene Ursache ausgeben. Kein URCap-Update vorgenommen.

## Tatsächlich ausgeführte Schritte

1. KameraNormal und aktuelle Einstellungen gelesen, Sicherung und VGA-Foto.
2. Ausschließlich eigenes bisheriges Qt-Kamerafenster gezielt beendet, ohne
   dessen ältere Öffnungswerte zurückzuschreiben; Nutzerwerte separat gesichert.
3. `POST /beginbarcode` und`POST /create?barcodeType=0`: beide akzeptiert.
4. Gesicherte Nutzereinstellungen im neuen Zustand erneut angewendet.
5. `POST /process`: abgewiesen mit49156. Erster Lauf sofort abgebrochen und
   wiederhergestellt. Präzisierte Nachprüfung akzeptiert diese eine bekannte
   Verarbeitungsfehlermeldung ausschließlich für anschließende lesende
   Modulbild-/Quellgrößenprüfung; keine HD-Quelle bestätigt, kein Export.
6. `POST /rejectmodule`, StatusNormal, ursprüngliche Einstellungen zurückgesetzt
   und kritische Bedienwerte geprüft. In beiden Läufen`restore_ok:true`, keine
   Abweichungen. Keine automatische Service-/Controller-/Weltpause oder Neustarts.
7. Qt-Kamerafenster wieder lesend geöffnet, tatsächlicher Bildempfang bestätigt.

Wiederhergestellte Nutzerwerte: Fokus404/Manual, Belichtung60000µs/Manual,
Gain16(API,1×), LEDManual/53(API,ca30%), EV0. Vollständige ursprüngliche
Einstellungen und Rücklesewerte in den Sitzungen. Keine Motorbewegung,
keine Power-/Brake-/Programm-/Adminänderungen. Diesmal kein Kameradienstausfall.

## Werkzeug und Nachweise

Experimenteller Helper`uwa_cell_control.wrist_hd_probe`; ohne`--execute` nur
Erklärung, keine Verbindung. Mit expliziter Ausführung verwendet er ausschließlich
das Inventar für right_rear, eine gemeinsame Kamera-Dateisperre, Statusprüfung,
laufend geschriebenes Report-JSON und`finally`-Wiederherstellung. Kein fertiger
HD-Knopf oder erfolgreicher HD-Client. Nicht parallel zur Aufnahme benutzen.

```bash
source ~/UWA_ws/src/multi_arm_manipulation_UWA/scripts/control_env.bash
python3 -m uwa_cell_control.wrist_hd_probe
```

Reale Reports:

- `setup/calibration/wrist_hd/20261110_201622/report.json`: ursprünglicher Test,
  Verarbeitungsfehler, Restore erfolgreich; Lizenz-/Statusdiagnose daneben.
- `setup/calibration/wrist_hd/20261110_201815/report.json`: präzisierte lesende
  Nachprüfung, `module_preview.jpg`, Mapping640/480, Restore erfolgreich.
- `setup/logs/uwa-wrist-hd-probe-{live,source-check}.log`.
- `setup/logs/uwa-wrist-after-hd-probe/report.json`: neues Fenster mit Livebild.
- Drei lokale Tests mit Kameradoppel prüfen Wiederherstellung bei Fehlern sowie
  Unterdrücken des nativen Exports bei unbestätigter HD-Quelle, einschließlich
  tatsächlicher49156-Meldung. `setup/logs/uwa-wrist-hd-probe-tests.log`.

Keine Bilddaten/Herstellerbinaries einchecken. Weiterer offener Schritt ist die
gezielte Diagnose des Modulprozesses beziehungsweise eine verlässliche direkte
Abfrage desHD-Pufferzustands. Bisherige Analyse-/Alternativbeschreibung:
[UCC4-Vergleich](wrist_ucc4_analysis_2026-11-10.md).
