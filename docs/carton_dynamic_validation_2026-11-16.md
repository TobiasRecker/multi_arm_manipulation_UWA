# Karton: Kraftmessung und schnelleres Simulationsprofil

Nutzerangaben: leerer Karton **500 g**, Belastungsreferenz **50 N an einer
einzelnen Backe/Wandkontaktfläche**. Die 50 N sind keine vermessene Bruchgrenze.

Der direkte Messpfad ist für diese Simulationsversuche nutzbar; eine zusätzliche
federnd gelagerte Roboterbasis wird derzeit nicht benötigt. Zwölf Referenzfälle
mit bekannten Lasten, Beschleunigungen, Gelenkreaktionen und Fallimpulsen
bestanden. Eine separate Integration mit 500 g ergab 4,904986 N Auflagekraft
gegenüber 4,905 N Sollwert. Nachweise liegen unter `setup/tasks/` im Workspace:

- `force_reference_20261116_matrix01/force-validation.json`
- `carton_force_observation_20261116_01/force-observation.json`

## Tatsächlich ausgeführte Greif- und Stoppversuche

| Versuch | Profil | Ergebnis |
| --- | --- | --- |
| Vollständiger Zyklus ab Vorposition | 5 mm/s, Arm 0,025 / Finger 0,6 rad/s | PASS, 29,925 mm Hub |
| Zwei vollständige Zyklen ab Home | 10 mm/s, Arm 0,05 / Finger 0,15 rad/s | 2/2 PASS, 29,924 mm Hub |
| Zwei weitere vollständige Zyklen ab Home | 10 mm/s, Arm 0,05 / Finger 0,2 rad/s | 2/2 PASS, 29,924 mm Hub |
| Armstopp unter Last | 10 mm/s, Arm 0,05 / Finger 0,2 rad/s | PASS, maximal 0,240 mm Relativfehler |
| Ablaufsteuerung unter Last pausiert | gleiches Stopp-Profil | PASS, maximal 0,238 mm Relativfehler |
| Kollisionswächter unter Last pausiert | gleiches Stopp-Profil | PASS, maximal 0,237 mm Relativfehler |

Die neuesten Home-Zyklen mit 0,2-rad/s-Fingergrenze hatten lückenlose Kraftdaten,
höchstens 5,504 N je Backe als konservative Peakobergrenze und maximal 0,274 mm
Relativfehler. Alle vier Kontakte blieben bis zum unterstützten Öffnen erhalten.
Die älteren 0,15-rad/s-Zyklen hatten höchstens 5,556 N Peakobergrenze.
Die drei Stoppfälle blieben unter
5,394 N Peakobergrenze und 5,146 N im 10-ms-Mittel. Beide Arme hielten bei
erhaltenem Griff. Bestätigungen einschließlich Stillstandsfenster erfolgten
nach 1,285 / 1,600 / 1,370 s; das sind **keine reinen Bremszeiten**.

Die Stoppfälle enden absichtlich im Zustand `FAILED`: Das Rezept wurde durch
den injizierten Fehler gestoppt. `fault-test-report.json: passed=true` und die
separate Kraft-/Versionsprüfung entscheiden über den bestandenen Stoppversuch.
Kein automatisches Öffnen, Zurückfahren oder Wiederaufnehmen der Bewegung.

Das neue Profil mit 0,2 rad/s Fingergrenze berücksichtigt diese größere Grenze
vollständig in seiner geometrischen Stoppreserve. Genau dasselbe Profil und
dieselbe gebundene Implementierung bestehen nun zwei ganze Home-Zyklen und
alle drei Stoppfälle. Die älteren Ergebnisse behalten ihr ursprüngliches Profil.

Nachweise: `carton_contact_preload_20261116_01/`,
`carton_preload_home_20261116_01/`, `carton_preload_home_20261116_02/`,
`carton_preload_faults_20261116_03/`. Die letzten beiden Matrizen enthalten
separate `cleanup-audit.json`: Codebindung aller fünf Fälle gültig, eigene
Prozesse beendet, äußerer Exitcode jeweils 0. Der gemeinsame versiegelte Index
mit exaktem Profil und Quelldateihashes ist
`setup/tasks/manipulation_qualification_20261116/result.json`.

## Was sich am Ablauf geändert hat

Die virtuelle Motorsteifigkeit wurde von 10 auf 30 Nm/rad und die Motorgrenze
von 0,35 auf 0,7 Nm erhöht. Die elastische Getriebegrenze bleibt 0,35 Nm.
Das behebt im untersuchten Modell die zu große Greifernachgiebigkeit bei 500 g.
Reibwert 0,6, Greiferdämpfung und diese Reglerparameter bleiben ungemessene
Annahmen. Es gibt keine kalibrierte Zuordnung zu realen Robotiq-Einstellungen.

Das 10-mm/s-Profil plant den 30-mm-Hub in etwa 5,74 Simulationssekunden,
gegenüber rund 114,75 s beim alten 0,5-mm/s-Profil. Die Einfahrt dauert etwa
7,04 statt mindestens 30 s. Grobes und feines Greiferschließen sind fünfmal
schneller parametriert. Bildaufnahmen, Planung und Agentenreviews zählen
getrennt; eine zwanzigmal kürzere Gesamtzykluszeit wurde nicht nachgewiesen.

Ab Kontakt bleibt ein starrer Greifverbund mit eingefrorenen Objekt→TCP-
Transformationen bestehen. Eine Objektbahn, eine gemeinsame Zeitparametrierung
und eine Zwölfgelenkaktion bestimmen die Bewegung beider tragender Arme.

## Versionen und Grenzen der Aussage

Parallele Arbeiten erweitern die aktuelle Codebasis um eine Kartondrehung.
Die Stoppmatrix verwendet deshalb den eigenen unveränderlichen Teststand
`setup/tasks/carton_frozen_baseline_20261116_01/`: erfolgreiche Home-Taskmodule,
erweiterte Szenenbindung und kopierte lokale Abhängigkeiten/Binärdateien.
Der gemeinsame Checkout wurde nicht zurückgesetzt. Die separate Drehung ist
durch diese Translations- und Stoppversuche nicht qualifiziert.

Für einen weiteren schnellen Translationsversuch aus dem Workspace:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
source setup/tasks/carton_frozen_baseline_20261116_01/environment.bash
python3 setup/tasks/carton_frozen_baseline_20261116_01/tools/explore_manipulation.py \
  --config setup/tasks/manipulation_qualification_20261116/qualified-profile.yaml \
  --reference setup/tracking/models/carton_avocado_v1/reference.npz \
  --output setup/tasks/NEW_UNIQUE_RUN --object-speeds 0.01 --repeats 1
```

Die drei Bild-/Bahnreviews übernimmt der Agent wie in der Bedienung beschrieben.
Ein bestehender Greiflauf muss vorher beendet sein. Der historische langsame
Paketdefault bleibt separat; der obige Aufruf wählt das getestete Profil explizit.

Frühere Fehlversuche bleiben erhalten: zu große Stoppreserve, passive
Fingergrenzüberschreitungen, zu nachgiebiger Griff, Empfangslücke, verpasstes
Agentenreview und zwischenzeitliche Quellenänderungen. Insbesondere die
Stoppmatrizen 01/02 sind keine vollständig bestandenen Matrizen.

Direkte Kontaktwerte werden als Beträge je Backe ausgewertet: Die rohe
Gazebo-Zuordnung von Kraftvektoren zu body1/body2 war bei umsortierten
Kollisionen unzuverlässig. Starre Aufprallpeaks hängen stark vom Zeitschritt
ab. Der Karton kann im Modell nicht knicken; die Armaktuation ist idealisiert.
Die Ergebnisse belegen daher weder eine physische Höchstgeschwindigkeit noch
eine Hardwarefreigabe. Für den realen Ablauf bleiben Kraft-/Dynamikabgleich
und daraus abgeleitete Reserven erforderlich.

[Bedienung und Experimenttreiber](manipulation_pipeline.md).
