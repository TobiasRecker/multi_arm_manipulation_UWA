# Kamera vorne links: konkreter Diagnoseauftrag

Stand16.11.2026. **Kein nachgewiesener Hardwaredefekt.** Das verwendete native
HD-Verzeichnungsprofil funktioniert in der zentralen Prüfregion gut, zeigt aber
problematische Extrapolation zum Rand. Deshalb bleiben LF-Bilder im aktuellen
Digitalisierungsauftrag diagnostisch. Kameraidentität/Fokus/Auflösung passen.
Originale, Qualitätsflags und aktive Kalibrierprofile wurden nicht verändert.

## Gerät und genau verwendetes Profil

- Arm `left_front`, IP192.168.8.2, UR5CB3; physische Kamera `028E1F350009061C`.
- Native JPEG2592×1944, **Fokus245 manuell während Aufnahme**. Nach Aufnahme
  ursprünglichen Autofokus wiederhergestellt. Readback im Leerlauf ist deshalb
  kein Nachweis des Aufnahmefokus; `record.json/settings_before` verwenden.
- Intrinsics: `setup/calibration/hardware_handeye/left_front_hd_20261112/intrinsics.json`.
  Registry: `config/digitization/native_optics.json`, `metric_default:false`.
  Dieser Eintrag ist eine bewusste vorhandene Ausschlussentscheidung.
- K: fx2677,462590, fy2687,526098, cx1297,590016, cy909,745503.
  Brown5 in OpenCV-Reihenfolge `[k1,k2,p1,p2,k3]`:
  `[-0.077040412, 3.696339814, -0.000308065, 0.010882868, -21.560299874]`.

## Drei getrennte Befunde

**1. Die ursprüngliche zentrale Intrinsics-Prüfung hat bestanden.**
41HD-Bilder,33Fit/8Prüfung, Fit-RMS0,316px, Prüfmedian0,336px,
Prüfmaximum0,413px. Die beobachteten Ecken lagen ungefähr in
x648–1810/y641–1445px. Das ist keine Prüfung des ganzen Sensors.
Siehe [ursprüngliche HD-Auswertung](left_front_hd_calibration_2026-11-12.md).

**2. Die getrennte HD-Hand-Auge-Prüfung hat nicht bestanden.**
Prüfmedian1,593px bei1,00px Grenze; Boardstreuung0,899mm/0,173° innerhalb
der damaligen Grenzen. Das ist ein anderer Test. Die Digitalisierung bestimmt
ihre Kameraposen direkt aus den sichtbaren Boards; sie benutzt für diesen
Residualtest weder Hand-Auge noch Roboter-FK. Daher erklärt ein schlechter
Hand-Auge-Fit allein die folgenden direkten Boardfehler nicht.
Die frühere VGA-Reihe bei640×480/Fokus245 hat bestanden; ihre K/D nicht einfach
aufHD übertragen. [VGA-Auswertung](left_front_calibration_2026-11-12.md).

**3. Native Board-Reprojektion am Rand ist aktuell deutlich schlechter.**
Vorbereitete Ansichten im unveränderten Auftrag
`setup/digitization/student_robot_20261113/job/prepared/camera_models.json`:

| Ansichts-ID im Auftrag | Ecken rechtes Board | x-Bereich px | y-Bereich px | direkter Board-RMS px |
| --- | ---: | ---: | ---: | ---: |
| r1_left_front |24|200–636|658–821|5,430|
| r2_left_front |20|63–549|448–570|55,683|
| r3_left_front |11|362–716|516–648|1,987|
| r4_left_front |24|178–635|474–601|12,110|

IDs sind **Importreihenfolge**, nicht chronologische Fahrreihenfolge. r2 ist
der spätere stationäre Wiederholsatz. Alle vier Bilder sind auf Identität,
Auflösung, Fokus und Hash geprüft; Bild-/Boardpunkte und Pfad stehen im JSON.
Der Fehler ist der native Pixel-RMS eines einzelnen direkt beobachteten Boards;
kein Welt-/Tisch- oder Objektmodellprior ist dafür nötig.

Schon am13.11. zeigte der Kartonscan LF-Inkonsistenz: rechts3,59px/links8,74px
Board-RMS, separate Kartonmaße kleiner als bei anderen Kameras. Das ist ein
zusätzlicher historischer Befund, kein Beweis für dessen einzige Ursache.
[Kartonvergleich](carton_multiview_2026-11-13.md).

## Mathematisch nachgewiesenes Extrapolationsproblem

Der radiale Anteil des gespeicherten Brown5-Modells lautet
`r_d = r*(1+k1*r²+k2*r⁴+k3*r⁶)`. Seine Ableitung wird bei idealem normiertem
Radius **r=0,485246** null und danach negativ (bei r0,50 bereits−0,260832).
Der radiale Anteil ist dort also nicht mehr monoton. Dies ist aus genau dieser
Datei berechnet, keine gemessene Eigenschaft der realen Linse. Tangentialanteile
sind in dieser eindimensionalen Ableitung nicht enthalten; sie ist keine
vollständige2D-Kalibrierprüfung. Ein starkes Modellproblem außerhalb des
beobachteten Bereichs ist damit konkret belegt; der Anteil an jedem einzelnen
Bildfehler muss noch experimentell getrennt werden.

Nachweis/Plot unter
`setup/digitization/student_robot_20261113/resume_20261116/left_front_diagnosis/`.
Rein offline reproduzierbar, mit neuem Ausgabeordner:

```bash
python3 src/multi_arm_manipulation_UWA/tools/diagnose_digitization_camera.py \
  --job setup/digitization/student_robot_20261113/job \
  --output /tmp/uwa-lf-optics-diagnosis
```

## Sinnvolle parallele Bearbeitung

1. Zuerst **offline** Originalbeobachtungen mit reduzierten Modellen vergleichen:
   Brown5 mit k3=0 und gegebenenfalls weniger freien Termen. Dieselben33Fitbilder,
   dieselben8unabhängigen Prüfbilder beibehalten; neue Ergebnisse separat ablegen.
   Zentrale Verbesserung allein validiert den Rand noch nicht. Randmonotonie und
   Invertierbarkeit prüfen; Änderungen an K/D nicht automatisch übernehmen.
2. Aktuelle vier Scanbilder als zusätzliche Randdiagnose verwenden. Wenn diese
   zum Modellwählen/Fitten verwendet werden, sind sie keine unabhängige Endprüfung
   mehr. PnP-Konvergenz/Mehrdeutigkeit bei schmaler, schräger Boardansicht und
   einzelnen Ausreißerecken getrennt untersuchen; Originalkorrespondenzen erhalten.
3. Für einen späteren neuen **Aufnahmeauftrag** frische Prüfbilder mit Board in
   Bildmitte, vier Rändern und Ecken, verschiedenen Abständen/Neigungen planen.
   Fokus245/native2592×1944 festhalten, Boardmaß/Planlage/Unschärfe prüfen.
   Das ist hier keine Freigabe für neue Armfahrten oder Profilaktivierung.
4. Erst nach direkter Intrinsics-/Randprüfung die Hand-Auge-Reihe neu beurteilen.
   Belichtungszeit/Unschärfe, Planar-PnP und Zeitpunkt der Werkzeugpose sind
   mögliche zusätzliche Ursachen, bislang nicht bewiesen.

Der Stillstandsfehler des später verworfenen dritten Scansatzes
(LF-Geschwindigkeitssignal0,020229rad/s) und das Beenden von GUI/Runner mitExit143
sind **separate Ablaufbefunde**, keine bewiesene Ursache der Optikfehler.
Der bestätigte kamera-only-Wiederholsatz ersetzt diesen Satz im Auftrag.

Parallelvertrag: Diagnose-/Fitversuche in eigenen Ausgabeordnern durchführen;
`intrinsics.json`, `native_optics.json`, aktive Profile und vorbereitete
Originalmodelle nicht während der Rekonstruktion überschreiben. Eine neue
Variante mit Quellenhash und Prüfergebnissen dokumentieren, dann gezielt bewerten.
