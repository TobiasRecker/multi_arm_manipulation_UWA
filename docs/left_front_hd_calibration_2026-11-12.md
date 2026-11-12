# Native HD-Kalibrierung des UR5 vorne links

2026-11-12, Australia/Perth. `left_front`, UR5 CB3, Kamera `028E1F350009061C`.
Erfasst wurden 41 native JPEG-Ansichten bei 2592 × 1944, Fokus 245 manuell,
Belichtung 60.590 µs und Gain 19. 33 Fitbilder und acht vorab reservierte
Prüfbilder; 39 mit 24 ChArUco-Ecken und zwei mit 22. Für jeden Burst sind
Sensor-Readbacks, Frische und Rückstellung der ursprünglichen Kameraeinstellungen
bestätigt. Keine Annahme einer zeitlich synchronisierten Belichtung.

| Unabhängige Prüfung | Ergebnis | Grenze | Status |
| --- | ---: | ---: | --- |
| Intrinsics, medianer RMS | 0,336 px | ≤ 1,00 px | bestanden |
| Intrinsics, höchster RMS | 0,413 px | ≤ 1,50 px | bestanden |
| Hand-Auge, medianer Reprojektions-RMS | 1,593 px | ≤ 1,00 px | nicht bestanden |
| Board-Translationsstreuung | 0,899 mm | ≤ 5 mm | bestanden |
| Board-Rotationsstreuung | 0,173° | ≤ 0,5° | bestanden |

Der HD-Intrinsics-Fit selbst hat einen RMS von 0,316 px. Die Ecken decken
x ≈ 648–1810 px und y ≈ 641–1445 px ab; Verzerrungsparameter an den äußeren
Bildrändern sind mit dieser Messreihe nicht gleich gut geprüft. Die native
Auflösung und der feste Fokus gehören zur Gültigkeit des Intrinsics-Profils.

Die Hand-Auge-Schätzung bleibt **diagnostisch**. Am festen linken Board ergibt
sie relativ zum `left_rear_base_link` eine Basisdistanz von 1414,55 mm; die
Basispose weicht um 1,86 mm Translation und 0,172° Rotation vom validierten
VGA-Ergebnis ab. Diese Übereinstimmung ist keine absolute Genauigkeitsmessung
und ersetzt den verfehlten HD-Pixelgrenzwert nicht. Weder HD-TF noch Intrinsics
wurden als aktives Profil eingetragen. Die validierte VGA-Kalibrierung bleibt
unverändert. Bei einer neuen Messung mehr Ansichten an den Bildrändern und neue
unabhängige Prüfbilder vorsehen.

Der erste Abbruch war der ROS-Stillstandscheck: Die parallel gestartete Reihe
hinten rechts änderte eine im freigegebenen Plan als fest behandelte Stellung.
Nach Ende der hinteren Reihe wurde der bestehende Weg mit allen vier echten
Gelenkstellungen erneut geprüft. Beim zweiten Abbruch verlor der CB3 die
External-Control-Verbindung kurz nach einem 56-ms-Steuerzyklus (Soll 8 ms);
Kausalität nicht nachgewiesen. PolyScope meldete NORMAL und `ros.urp` STOPPED.
Der geladene External-Control-Knoten wurde über den vorhandenen ROS-Dienst
neu gestartet, der Restweg erneut geprüft und weiter aufgenommen. Ein beendeter
lokaler Aufnahmeprozess nach erfolgreich erreichter Pose 037 wurde durch ein
stationäres Bild ersetzt. Abschließend: NORMAL, External Control verbunden,
eigener Fahrcontroller inaktiv, kein Rückfahrziel.

Sitzung: `setup/calibration/hardware_handeye/left_front_hd_20261112/` mit
Originalen, Beobachtungen, Prüfergebnissen, Resume-Plänen und Protokollen.
