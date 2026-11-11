# Front-Kamera:62-Bilder-Versuch und Bildzahlvergleich

Die konkret freigegebene Reihe wurde vollständig aufgenommen: **50 Fit- und
12 vorab reservierte Prüfbilder**. Alle62 Bilder sind akzeptiert, mit14…24
ChArUco-Ecken; kein Prüfbild wurde zum Fit verwendet.640×480, fester manueller
Fokus435. Die Roboter stehen am Ende; keine automatische Rückfahrt.

## Ergebnis

| Prüfung | Wert | Grenze | Ergebnis |
|---|---:|---:|---|
| Intrinsics Fit-RMS |0,289px |1px |bestanden |
| Intrinsics Prüf-RMS, Median |0,299px |1px |bestanden |
| Hand-Auge Prüf-Reprojektion, Median |0,748px |1px |bestanden |
| Boardpositions-Konsistenz, RMS |2,344mm |5mm |bestanden |
| Boardrotations-Konsistenz, RMS |0,652° |0,5° |**nicht bestanden** |

Damit ist die **Intrinsics-Auswertung gültig nach unseren Kriterien**, das
**Hand-Auge-Profil nicht freigegeben und nicht aktiviert**. Das frühere gültige
Rear-Profil bleibt separat erhalten. Die Zahlen beschreiben interne Konsistenz,
keine unabhängig vermessene absolute Genauigkeit. Aus dem fehlgeschlagenen
Frontprofil wird keine kalibrierte relative Basis-/Tischpose aktiviert.

## Bringt die höhere Bildzahl etwas?

Innerhalb derselben Front-Kamera wurden20/33/50 Fit-Bilder jeweils gegen
dieselben zwölf Prüfbilder ausgewertet. Bei20 und33 vier feste zufällige,
verschachtelte Teilmengen; bei50 einmal der vollständige Satz. Angegeben ist
die Spannweite dieser Auswahlen, **kein Konfidenzintervall**.

| Fit-Bilder | Hand-Auge Prüf-Reprojektion [px] | Boardpositions-RMS [mm] | Rotations-RMS [°] |
|---:|---:|---:|---:|
|20 |0,720–0,805 |2,20–2,73 |0,623–0,775 |
|33 |0,723–0,779 |2,27–2,45 |0,607–0,745 |
|50 |0,748 |2,34 |0,652 |

Die höhere Bildzahl zeigt hier **keinen klaren großen Qualitätsgewinn**;
alle Auswahlen verfehlen die Rotationsgrenze. Das ist kein formaler
Signifikanztest. Die größere Bildabdeckung ist tatsächlich erreicht:
Ecken ungefähr x117…586/y76…402 gegenüber x140…431/y123…341 in der Rear-Reihe.
Der direkte Front-/Rear-Fehlervergleich isoliert die Bildzahlwirkung nicht,
weil physische Kamera, Fokus, Montage und Sichtwinkel verschieden sind.

Vor weiteren Aufnahmen sollte die Rotationsinkonsistenz gezielt diagnostiziert
werden. Mögliche Beiträge aus Bild-Pose-Schätzung, Optikmodell, Board oder
mechanischer Stabilität sind bisher nicht getrennt nachgewiesen. Es wurde
weder die Rotationsgrenze erhöht noch ein zufällig günstigerer Fit ausgewählt.

## Unterbrechungen und Wiederaufnahme

-043: Kabel vor der Kamera, nur9 Ecken. Anhalten/Front deaktiviert, schlechte
  Dateien samt SHA256 separat aufbewahrt. Nach Nutzer-Kabelsicherung ohne
  Montage-/Boardänderung gleiche Pose mit24 Ecken neu erfasst. Neun gemeinsame
  Ecken verschieben sich im Median nur0,025px, Maximum0,063px.
-060: nativer C153A5, Wrist3-Bahnabweichung. Nutzer bestätigt und beseitigt
  Kabelspannung. Wartenden Auftrag gecancelt, Front inaktiv bestätigt; keine
  automatische Schutzstoppquittierung. Nach nativem NORMAL-Zustand die zwei
  ursprünglichen Restziele aus neuen aktuellen Winkeln geprüft/ausgeführt.
  Kamera nach Wiederanlauf von424Auto auf das geprüfte435Manual-Profil
  zurückgesetzt. Keine ungesehenen Ersatz-Zielposen.

Die reale Stop-Meldung stammt aus dem UR. [UR beschreibt C153A5 als
Bahnabweichung, erkannt an Wrist3](https://www.universal-robots.com/manuals/EN/HTML/SW5_25_1/Content/prod-err-codes/topics/CODE_153.html).
Die Kabelursache wurde vom Nutzer vor Ort bestätigt.

## Dateien und Wiederholung

Unter `setup/calibration/hardware_handeye/right_front_20261111/`:

- `records/`:62 Rohbilder, Annotationen, tatsächliche Gelenke/Werks-FK und Ecken.
- `rejected/sample_043_attempt_01/`:erster abgelehnter Versuch unverändert.
- `analysis_60_views/`:fehlgeschlagener60er-Zwischenstand separat erhalten.
- `evaluation_v1/`:versionierte vollständige Bewertung mit SHA256-Manifest,
  Intrinsics/Hand-Auge-JSON, Prüfgrafik und Bildzahlvergleich.
- `count_comparison/comparison.json`:alle Teilmengen, Prüfeinzelwerte und
  Parameterunsicherheiten; kein aktives Profil ausgewählt.
- `completion_state.json`:bestätigter Endzustand beider Arme.

Offline erneut vergleichen:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
python3 -m uwa_cell_control.count_comparison \
  setup/calibration/hardware_handeye/right_front_20261111 --counts 20,33,50 \
  --output setup/calibration/hardware_handeye/right_front_20261111/count_comparison
```

Rohdaten und gespeicherte Profile werden durch den Vergleich nicht verändert.

Front hält am Ende die letzte Aufnahmepose, Rear seine Parkpose; beide nativen
skalierten JTC aktiv, sonstige Bewegungscontroller inaktiv. Hardware-GUI und
Treiber bleiben offen, eigene Domain68-Vorschauen sind geschlossen. Der neue
Watcher reagiert auch auf echte UR-Safety-Stops bei weiterhin wahrem Programmlink;
keine neuen manuellen GUI-Freigabegates.22 abschließende gezielte Tests und drei
frühere Standard-Vierarm-/Fit-/Holdout-Regressionen bestanden.
