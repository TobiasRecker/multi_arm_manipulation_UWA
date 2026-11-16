# Wiederaufnehmbare Objektdigitalisierung

Stand13.11.2026: erste ausführbare Version, `scripts/digitize.sh`. Routinedurchläufe
verwenden JSON-Daten und feste Programme. Sie erzeugen keinen neuen Quellcode je
Objekt. [Skill für ausführende Agenten](../.agents/skills/uwa-digitize/SKILL.md).

Unterstützte Formen: einfache offene rechteckige Schale (`box_shell`) und
rechtwinklige Platten-/Profilkonstruktion (`plate_l`). Komplexe Maschinen wie
der [studentische Roboter](student_robot_digitization.md) verwenden
`multiview_mesh`: Aufnahme, Datenprüfung und Rekonstruktionsauftrag sind verfügbar,
aber **noch kein validierter dichter Mesh-Backend**. Dieser Fall meldet benötigte
Ansichten/Masken/Backend; ein ungeeigneter Quader wird nicht als Ersatz ausgegeben.

Seit16.11. gibt es zusätzlich einen eigenständigen, getesteten
[Silhouetten-Mesh-Prototyp](student_robot_visual_hull.md) mit Fotoexport.
Er erzeugt ausdrücklich einen unvalidierten Außenhüllenkandidaten und ist noch
nicht als Standardbackend dieses Jobs registriert. LF-Befunde zur parallelen
Reparatur: [Kameradiagnose](left_front_camera_diagnosis_2026-11-16.md).

## Auftrag anlegen und fortsetzen

Aus `/home/rosmatch/UWA_ws`; Aufträge und Rohdaten bleiben unter
`setup/digitization/`, nicht im Git. Ein bestehender Auftrag wird nicht überschrieben.

```bash
job_dir="$PWD/setup/digitization/example/job"
bash src/multi_arm_manipulation_UWA/scripts/digitize.sh init \
  --job "$job_dir" --id example_object --family plate_l --size-m .30 .18 .18 \
  --known-dimensions /absolut/known_dimensions.json --views-per-wrist 1
bash src/multi_arm_manipulation_UWA/scripts/digitize.sh status --job "$job_dir"
```

`--size-m`: grobe Außenmaße in **Metern**, als Nutzerangabe gekennzeichnet.
`known_dimensions.json` enthält bei `plate_l` beispielsweise
`{"plate_thickness_m":0.01,"profile_size_m":0.02}`, bei `box_shell`
`{"wall_thickness_m":0.0025}`. Unbekannte Materialstärken werden nicht vermessen
behauptet; vor dem Fit sind sie erforderlich. `multiview_mesh` braucht diese
einfachen Materialparameter nicht. `--views-per-wrist` bezeichnet unterschiedliche
Kamerastandpunkte, nicht wiederholte Bilder derselben Stellung.

`status` liefert Objekt-ID, Zustand, nächsten Schritt, Stufen-/Fehler-/Zeitangaben
und getrennte Qualitätswerte. Es fragt keine Geräte ab und bleibt während eines
laufenden Jobs lesbar. Eine verwaiste RUNNING-Markierung wird bei freier
Auftragssperre als unterbrochen gemeldet; nichts startet automatisch neu.

## Bilder übernehmen oder aufnehmen

```bash
# Offline: vorhandener vollständiger nativer Fünfkamera-Satz.
bash src/multi_arm_manipulation_UWA/scripts/digitize.sh ingest \
  --job "$job_dir" --manifest /absolut/set_TIMESTAMP/manifest.json

# Explizit Kamera-Hardware verwenden, alle Arme müssen bereits stillstehen.
# Kein Start von Treibern, Power/Brake/Play oder Bewegung.
bash src/multi_arm_manipulation_UWA/scripts/digitize.sh capture \
  --job "$job_dir" --telemetry-source rtde
```

ROS ist der Standardbeobachter; `rtde` liest ausschließlich Controller-Ausgaben.
Der bestehende Capture führt Kamera-/Fokus-/LED-Nutzung und unabhängige
Stillstandsprüfung aus. Verbindungsaufbau erhält2s Pakettimeout; der laufende
RTDE-Datenstrom weiterhin0,4s und der Wächter0,5s Frischegrenze. Keine lockeren
Stillstandsgrenzen zugunsten erfolgreicher Fotos.

Ein weiterer ausdrücklich angeforderter Satz braucht `capture --new-view`.
Das bewegt keinen Arm. Neue Stellungen benötigen getrennte Planung und den
vorhandenen überwachten Bewegungsablauf. Weder Aufnahmen noch Bewegungen
werden beim Fortsetzen einer Offlineberechnung erneut ausgeführt.

Import prüft vollständige Kameraliste, Erfolg, durchgehenden Stillstand, native
Bildgrößen und Bild-/Datensatzhashes. `all_full:false` ist erlaubt, sofern das
Set ansonsten gültig ist; einzelne fehlende Boardposen bleiben später explizit
ausgeschlossen. Ein unbestätigter Satz wird nicht als gültige Akquisition importiert.

Bei fehlgeschlagener Wiederherstellung bleiben Versuch und Originale erhalten;
weitere Captures werden gesperrt. **Erst bei wieder verfügbaren, freien Kameras**
explizit aufrufen:

```bash
bash src/multi_arm_manipulation_UWA/scripts/digitize.sh recover --job "$job_dir"
```

Dies stellt ausschließlich die gesicherten Kameraeinstellungen wieder her und
prüft sie; kein Controller-/Programmstart. Ein Stromausfall kann eine erfolgreiche
Wiederherstellung verhindern. Status/Offlinearbeit versuchen sie nicht heimlich.

## Vorbereiten, Form fitten und Texturen zuordnen

Für den schnellen Routinefall genügt **ein einziger Offlineaufruf**, sobald
Eck-/Flächendaten vorliegen:

```bash
bash src/multi_arm_manipulation_UWA/scripts/digitize.sh run --job "$job_dir" \
  --annotations /absolut/reviewed_landmarks.json --faces /absolut/reviewed_faces.json
```

Er bündelt Vorbereitung, Fit, Textur, Export und Prüfansichts-Tracking. Fehlende
Eingaben oder ein fehlgeschlagener Fit stoppen den Ablauf; nur ausdrückliches
`--draft` erlaubt den Entwurf. `run` nimmt keine neuen Fotos auf und startet
keine Geräte. Einzelne Schritte sind weiterhin gezielt aufrufbar:

```bash
bash src/multi_arm_manipulation_UWA/scripts/digitize.sh prepare --job "$job_dir"
bash src/multi_arm_manipulation_UWA/scripts/digitize.sh fit \
  --job "$job_dir" --annotations /absolut/reviewed_landmarks.json
bash src/multi_arm_manipulation_UWA/scripts/digitize.sh texture \
  --job "$job_dir" --faces /absolut/reviewed_faces.json
```

Optikquellen: `config/digitization/native_optics.json`, Prüfregeln:
`config/digitization/quality_v1.json`. Eigene Identität, Fokus und Auflösung je
Kamera; keine VGA-Substitution. Ursprüngliche PASS-/Fehlerflags bleiben erhalten.
LF bleibt aufgrund bisheriger nativer Inkonsistenzen diagnostisch; Ausschluss
ist sichtbar. Die Kamerapose wird aus beobachteten Boards bestimmt, ohne neue
Weltkalibrierung oder nominelle Roboterpose. Bei Bedarf wird eine ausdrücklich
beobachtete Zweiboard-Brücke verwendet. Rohdaten, K/D und vorbereitete Posen
werden nicht durch ein angenommenes Objektmodell ersetzt.

Landmarkformat: `proxy_width:1600`, `observations.<rN_camera>` mit `ids`,
`pixels`, `role:"fit"|"validation"` und Original-`image_sha256`. Koordinaten
gelten für das **ganze ungedrehte Bild** bei1600px Breite. Mindestens zwei
Fitansichten mit50mm Kamerabasis und eine vorab festgelegte Prüfansicht.
Eine Fitansicht mit Kantenpunkten2/3 erlaubt Initialisierung ohne alte Objektpose;
alternativ expliziter Startvektor `[board_x,board_y,yaw,W,D,H]` in m/rad.
Punktnummerierung folgt den festen Rezepten in `digitization_geometry.py`;
eine falsche Nummerierung ist kein durch Reasoning reparierter Messwert.

Texturformat: `proxy_width:1600`, `faces` mit `camera_view`,
`source_image_sha256`, vier `pixels` in UV-Reihenfolge(0,0),(1,0),(1,1),(0,1),
`origin_m`, orthogonalen `u_m`/`v_m` und `normal_sign:+1|-1` relativ zu u×v.
Das sind explizite Daten, keine neuen Pixelskripte pro Objekt. Die Texturen
berücksichtigen native Verzeichnung. Außerhalb des Originalbildes liegende
Abbildungen oder nicht zur CAD-Fläche passende Aperturen werden abgelehnt.
Nicht beobachtete Flächen bleiben einfarbig und als solche gekennzeichnet.

Der Fit verändert keine Intrinsics und nutzt Prüfbildpunkte nicht zum Schätzen.
Ausgangsgrenzen3px Fit-/5px Prüf-RMS beziehen sich auf1600px Vergleichsbreite.
Dies sind neue versionierte Modell-Prüfregeln; vorhandene problematische Daten
dürfen daran scheitern. Bildkonsistenz ist keine absolute Genauigkeit.

## Kandidat und Trackingprüfung

```bash
bash src/multi_arm_manipulation_UWA/scripts/digitize.sh export --job "$job_dir"
# Bei nicht bestandener Bildprüfung nur ausdrücklicher Entwurf, keine Freigabe:
bash src/multi_arm_manipulation_UWA/scripts/digitize.sh export --job "$job_dir" --draft
bash src/multi_arm_manipulation_UWA/scripts/digitize.sh track-check --job "$job_dir"
```

Export: STEP/mm, STL/GLB/DAE/m, vorhandene Fototexturen, Manifest, technische
Prüfungen und CPU-gerenderte Vorder-/Rückansicht. STEP-Rückimport, gleiche Maße,
geschlossenes zusammenhängendes STL und positives Volumen werden geprüft.
Kandidaten liegen versioniert unter `candidates/`; keine automatische Installation
in der Zelle, keine neue Kollision, Masse oder Manipulationsfreigabe.

`track-check` ist ein Einzelbildtest auf geometrischen Prüfansichten. Fotos,
die Assettexturen geliefert haben, werden dafür nicht als unabhängig akzeptiert.
Er ersetzt keinen3-Frame-Static-/Online-/Bewegungstest. Wenig Textur führt zu
NO_TEXTURE_REFERENCE, fehlende zuverlässige Wiedererkennung zu
NO_HELD_OUT_DETECTION. `manipulation` bleibt NOT_APPROVED.

## Wiederaufnahme, Nachweise und Grenzen

Eingabe-, Code-, Optik-, Regel- und Ergebnishashes bestimmen die Wiederverwendung.
Geänderte Eingaben oder beschädigte Ausgaben invalidieren nachfolgende Stufen;
Rohaufnahmen bleiben erhalten. Es gibt Auftragssperren, persistierte Fehler und
Abbruchzustände. Ctrl+C wird gespeichert; laufende native Transaktionen müssen
ihre vorhandene Wiederherstellung abarbeiten. Keine automatische Wiederholung.

Offline-Nachweise unter `setup/digitization/pipeline_offline_20261113/`: beide
Formfamilien mit vorhandenen echten Aufnahmen durchlaufen, technische Kandidaten
exportiert, PTFE mit zwei Fototexturflächen und unabhängiger Trackingprüfung.
Beide Modelle bleiben REVIEW_REQUIRED, PTFE ohne erfolgreiche Prüfansichts-
Erkennung. Vorhandene Originalassets und ihre Qualitätsflags wurden nicht ersetzt.
61gezielte Softwaretests und Lyrical-Build bestanden; weitere Timing-/Cache-
Nachweise stehen in diesem Ordner. Frühe Entwicklungsfehler bleiben dokumentiert.

Gemessener einzelner CLI-Aufruf am gespeicherten PTFE-Satz: **7,18s** für die
Verarbeitung nach letztem Codestand, **1,33s** bei anschließendem Cachetreffer,
jeweils einschließlich Shell-/Pythonstart. Punkte und Flächenzuordnungen lagen
bereits vor; keine Aufnahme, neue Bildinterpretation oder Agentenzeit enthalten.
Die Geometrie blieb REVIEW_REQUIRED und die Prüfansichts-Erkennung erfolglos.
Dies belegt schnelle Wiederverwendung, keine neue Genauigkeit oder Laufzeit
für ein unbekanntes komplexes Objekt. Nachweis `one_call_cli_timing_final.json`.

Noch offen: validierter dichter Mesh-Backend, automatische Masken-/Merkmals-
zuordnung, mehr unterstützte Formfamilien und ein tatsächlicher Vergleich der
Reasoning-Stufen. Diese Version ist ein getesteter erster Runner, kein universell
automatischer Scanner und noch kein Nachweis gleicher Qualität mit kleinerem Modell.
