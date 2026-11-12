# Gemeinsame Sichtstellungen real angefahren und HD-Bilder aufgenommen

Stand: **2026-11-12**, Australia/Perth. Nutzerauftrag: die vorgeschlagenen
Arme sequentiell in die Sichtstellungen fahren, anschließend Wrist-HD aufnehmen.
Im Verlauf hat der Nutzer links vorne zunächst zurückgestellt. Dort wurde
**kein Fahrziel gesendet**. Die drei anderen Ziele entsprechen unverändert
`oak_pose_20261112/design_wrist/proposal.json`.

## Ergebnis der Fahrten

Reihenfolge: **left_rear → right_rear → right_front**. Vollständige MoveIt-
Zelle und die neue individuelle Werkskinematik links vorne verwendet, keine
diagonalen Kollisionsausnahmen. Links vorne wurde statt einer erfundenen
Null-/Home-Pose fortlaufend ausschließlich über RTDE-Ausgaben beobachtet.
Dieser Client hat keine Input-Rezeptur, keinen Writer und sendet kein URScript.

| Arm | Endfehler, größtes Gelenk | Positionsänderung im letzten0,5s-Fenster | Native Safety | Aktive Motioncontroller |
|---|---:|---:|---|---:|
| left_rear |0,0000278rad |0,0000505rad | NORMAL |0 |
| right_rear |0,0000456rad |0,0000377rad | NORMAL |0 |
| right_front |0,0000282rad |0,0000505rad | NORMAL |0 |

Keine automatische Rückfahrt. Die drei Arme bleiben an ihren Aufnahmezielen.
Die Montage-/Tischgeometrie ist weiterhin vorläufig, keine absolute
Hardware-Kollisionskalibrierung aus dieser Erprobung abgeleitet.

Während der ersten hinteren rechten Fahrt setzte die linke Fronttelemetrie aus.
Eigener Action-Cancel und Controllerdeaktivierung funktionierten. Nach einem
25s-Test mit258 Paketen und maximal101ms Paketabstand wurden die Restwege neu
geprüft. Links hinten war bereits am Ziel und erhielt kein erneutes Fahrziel.
Der Reader beendet sich jetzt bei einem Nichtdaten-/Reconnect-Paket nicht
sofort; die bestehende0,5s-Frischeprüfung wurde nicht verändert. Ursache des
ersten Aussetzers ist nicht abschließend bewiesen. Kein Schutzstopp quittiert.

## Native Wrist-Fotos

Alle gespeicherten Original-JPEGs haben **2592×1944 Pixel**, keine Hochskalierung
oder Farbkorrektur. Jeweils alle **24 ChArUco-Ecken des eigenen Tischboards**
erkannt. Die hintere rechte Aufnahme zeigt zusätzlich das mobile Board.

Lokaler Ergebnisordner:
`$UWA_WS/setup/calibration/shared_views_20261112/`

- `photos/left_rear/native_hd.jpg` und `annotated.jpg`: erfolgreiche native
  Transaktion, Restore bestätigt,24Ecken.
- `photos/right_front/native_hd.jpg` und `annotated.jpg`: erfolgreiche native
  Transaktion, Restore bestätigt,24Ecken. Sichtbarer ursprünglicher Grünstich
  bleibt im unveränderten Original erhalten.
- `photos/right_rear/native_hd_diagnostic.jpg`: native Kameraaufnahme mit24Ecken.
  Der alte Dienst meldete einen echten Fokusfenster-Restorefehler; dieses
  fehlgeschlagene Dienstresultat bleibt unverändert und das Bild wird **nicht
  als freigegebene Kalibrierbeobachtung** ausgegeben.
- `wrist_hd_overview.jpg`: beschriftete Übersicht der drei Bilder.
- `motion_results/`, `executed_plans/`, `resume_plans/`, `completion-state.json`:
  aktuelle Zustände, tatsächlich ausgeführte Zielwege und Prüfnachweise.
- `summary.json`, `manifest.json`: Abschlussübersicht und Datei-Hashes.

Die ersten linken/hinteren und vorderen/rechten Dienstbilder wurden wegen beim
Aufruf nicht frisch eingelesener Telemetrie verworfen. Nach Einlesen der aktuellen
ROS-Werte direkt nach blockierendem HTTP-/Fokus-Setup verliefen beide Wiederholungen
erfolgreich; sämtliche Bewegungs- und Frischeprüfungen blieben erhalten.
Fehlversuche liegen unter `failed_photos_v1/` sowie den unveränderten nativen
Dienstverzeichnissen. Es gab keine weitere Armfahrt für die Wiederholung.

### Ältere hintere rechte Kamera

UCC1.11.1 verschiebt beim Schreiben des Fokusfensters dieY-Koordinate um16Pixel;
die ältere LED-Schreibcodierung ist zusätzlich invertiert. Der native Worker
konnte seinen eigenen Restore nicht bestätigen, obwohl alle drei HD-JPEGs
korrekt vorlagen. Der Fehler wurde nicht ignoriert oder zu PASS umgeschrieben.

Die ursprünglichen Konfigurationswerte **vor diesem Auftrag** wurden danach
über gezielte Kamera-Requests wiederhergestellt. Nach Kompensation der tatsächlich
beobachtetenY-Abweichung und der bekanntenLED-Codierung war der tatsächliche
Readback sämtlicher Konfigurationsfelder identisch; Kamera **Normal**.
Automatische Fokus-/Belichtungs-/Weißabgleichsausgaben sind variable Messwerte,
keine festen Einstellungen. Nachweis:
`right-rear-final-settings-restore-corrected.json`.

Diese manuelle Wiederherstellung behebt noch nicht den automatischen Legacy-
Dienst. Dessen Schutz gegen ungeprüfte Autofokus-Aufrufe bleibt bestehen;
weitere Serien brauchen eine separat geprüfte Worker-Korrektur oder ein
URCap-Update. Neue HD-Intrinsics wurden hier nicht geschätzt.

## OAK-Gegensicht nach den Fahrten

Zusätzlich über den vorhandenen HQ-Fotodienst ein neues natives8000×6000-Bild
aufgenommen. Alle drei Boards sind gleichzeitig vollständig erkannt:
**je17Marker und24ChArUco-Ecken**. Damit ist ihre Sichtbarkeit in dieser echten
Konfiguration nachgewiesen, ohne daraus eine garantierte Sicht für alle späteren
Bewegungen oder eine OAK-Extrinsikkalibrierung abzuleiten.

Originale: `setup/oak4/photos/20261112-150024-hq-6a5b0dea/`.
Beschriftete Übersicht/Detektionsdaten:
`shared_views_20261112/oak_post_motion/{boards-overview.jpg,detection.json}`.

## Kamera-SSH dauerhaft ohne Passwortdialog

Auf ausdrücklichen Nutzerauftrag ist der Schlüsselzugang aufallen4Controllern
installiert und durch frische BatchMode-Anmeldungen überprüft. Drei e-SerieURs
verwenden Ed25519; der alte linke vordere CB3 benötigt einen eigenenRSA3072-
Schlüssel und nur für diesenHost aktivierteLegacy-Signaturen. Bestehende fremde
Schlüssel wurden erhalten. Die Einträge erlauben nur diesenPC192.168.8.209,
keine Weiterleitungen oderPTY. Keine Passwörter gespeichert.

PrivateSchlüssel und dauerhaftesHostvertrauen liegen außerhalbGit unter~/.ssh.
Der Kamerabackend verbindet automatisch neu und prüftHostschlüssel weiterhin
streng. Kamera-SSH ist von der nativen Armsteuerung getrennt.
Siehe [Kameradienst](wrist_hd_service.md). Zwölf zugehörige Regressionstests
bestanden (`ssh-hd-tests.log`).

Links vorne wurde neu als192.168.8.2/UR5/Serial2017356443 eingebunden und seine
Werkskinematik ausgelesen. Der weitere Steuerungsstart bleibt Benutzerarbeit:
RTDE-Inputbesitz undExternalControl-Konfiguration noch abschließend prüfen.
Das zunächst fehlende ros.urp wurde inzwischen vom Nutzer geladen. Dieser
Auftrag hat dort weder eine Fahrt noch einen Programmstart ausgeführt.
