# Bildzahl und Qualität der ersten realen Kalibrierung

Stand2026-11-11. Nutzer fragt nach zusätzlichem Nutzen weiterer Bilder und
schlägt eine Front-Reihe mit etwa50% mehr Ansichten nach Rear-Parken vor.
Diese Bewertung verändert weder Hardwarezustand noch gespeicherte Profile.

## Bewertung vorhandener Daten

Die abgeschlossene Rear-Reihe besteht aus33 Fit- und8 vorab reservierten
Prüfansichten. Intrinsics und Hand-Auge bestehen die vorhandenen Gütegrenzen.
Das ist ein brauchbares erstes Profil im beobachteten Bereich; absolute
Genauigkeit wurde nicht gegen eine externe Messreferenz nachgewiesen.

Zusätzliche Offline-Diagnose: vier deterministische Zufallsauswahlen mit je20
und26 Fit-Bildern, jeweils gegen dieselben8 vom Fit ausgeschlossenen Prüfbilder.
Die33-Bilder-Lösung einmal als Referenz neu berechnet. Kamera-Matrix und
Hand-Auge werden für jede Teilmenge separat gefittet, keine Ground Truth.

| Fit-Bilder | Auswahlen | Intrinsics-Prüffehler, Median [px] | Hand-Auge-Prüffehler, Median [px] | Boardpositions-RMS [mm] |
|---:|---:|---:|---:|---:|
|20 |4 |0,222–0,223 |0,399–0,479 |2,26–2,88 |
|26 |4 |0,221–0,223 |0,424–0,501 |2,41–2,92 |
|33 |1 |0,222 |0,466 |2,66 |

Ergebnis: kein klarer monotoner Gewinn durch mehr Bilder innerhalb dieser
bereits erfassten Ansichten. Das beweist keine Sättigung bei62 Bildern und
ist kein statistischer Signifikanztest. Die nachträgliche Betrachtung der
Prüfdaten ist eine Diagnose, keine neue unangetastete Abnahme; das aktive
Ergebnis wird damit nicht ausgewählt/ersetzt.

Berichte: `setup/calibration/hardware_handeye/right_rear_20261111/quality_review/`
mit `subsets.json` und `summary.json`. Die versionierte Originalauswertung
unter `result_v1/` bleibt unverändert.

Die Ecken decken bisher ungefähr x140…431/y123…341 im640×480-Bild ab.
Bildränder sind nicht beobachtet; zusätzliche Bildpositionen, gut auflösbare
Abstände und Neigungen bieten deshalb voraussichtlich mehr neue Information
als ähnliche Wiederholungen. [OpenCV empfiehlt gleichmäßige Abdeckung der Bildebene](https://docs.opencv.org/4.x/d7/d21/tutorial_interactive_calibration.html)
und berücksichtigt neben Bildfehlern auch Abdeckung und Parameterunsicherheiten.

## Vorschlag für einen kontrollierten Front-Versuch

1. Rear aus aktuellen realen Winkeln kollisionsgeprüft parken; Frontstellung
   dabei live als Hindernis. Neue Wege vor physischer Fahrt prüfen/zeigen.
2. Eigenes Front-Profil bei konstantem manuellem Fokus und Bildmodus erfassen:
   ungefähr62 Aufnahmen, davon50 Fit und12 vorab ausschließlich zur Prüfung.
   Das bestehende rechte Tischboard bleibt unverändert an seinem Ort.
3. Bildabdeckung/Neigungen/Abstände gezielter variieren, soweit sichtbar und
   mit ganzer Zelle sowie nativen UR-Grenzen vereinbar.
4. Innerhalb derselben Front-Kamera mehrere Fit-Teilmengen (z.B.20/33/50)
   gegen dieselben12 Prüfaufnahmen vergleichen; diese nie zum Fit verwenden.
   Mehrere Teilmengenauswahlen für Streuung vorsehen, nicht das beste Ergebnis
   nachträglich herausgreifen. Eine zusätzliche unangetastete räumliche Prüfung
   ist für endgültige Modellwahl/Genauigkeitsnachweis sinnvoll.

Ein direkter Front-/Rear-Vergleich isoliert die Bildzahlwirkung nicht: gleiche
Kamerabauart bedeutet nicht dieselbe physische Kamera, gleichen Fokus oder
identische Intrinsics/Montage. Auch bei tatsächlich übertragener gleicher
Kamera wäre ihre Montage zum Flansch neu zu kalibrieren. Kameraseriennummern
zu den Armen sind bisher nicht verifiziert. Fokuswerte geräteübergreifend
nicht als identische optische Einstellung behandeln.

Das gemeinsame feste Board erlaubt anschließend die relative Transformation
der beiden rechten Roboterbasen aus ihren unabhängigen `T_base_board`-Schätzungen
zu berechnen. Das allein ist keine unabhängige absolute Genauigkeitsreferenz.

Der Front-Versuch wurde anschließend vom Nutzer akzeptiert und vollständig
durchgeführt. [Ergebnis mit62 Bildern und festem Prüfsatz](front_calibration_2026-11-11.md):
Intrinsics bestanden, Hand-Auge-Rotationsgrenze weiterhin verfehlt; kein klarer
großer Bildzahlgewinn im kontrollierten Vergleich. Hardware-Anzahlgrenzen
wurden dafür gezielt erweitert, Gütegrenzen und unabhängige Prüfansichten
blieben erhalten. Der obige Vorschlag beschreibt den vorab gewählten Versuchsplan.
