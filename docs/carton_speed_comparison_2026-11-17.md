# Simulierter Kraftvergleich 1× / 5×, 2026-11-17

Der gleiche Zweiarm-Hub wurde mit fünffach komprimierter Zeit ausgeführt. Der neue Versuch besteht den vollständigen vertikalen Hub-/Rücksetz-/Lösezyklus; die Kontaktlasten beim Hub bleiben nahe der langsamen Referenz. **Die 90°-Drehung wurde bei 5× nicht ausgeführt.**

## Gemessene Kontaktlasten

Verglichen wird der gemeinsame tatsächliche Hubbereich bis 99,947 % des Sollhubs (etwa 147,73 mm). Werte sind konservative Betragsobergrenzen pro Backe, keine vorzeichenrichtige resultierende Objektkraft. „10 ms“ bezeichnet das größte Mittel eines nativen 10-ms-Fensters; „Peak“ die größte Obergrenze aus den 0,5-ms-Physikschritten. Nichtzeitgleiche Kontaktspitzen können in dieser Obergrenze aufsummiert sein.

| Backe | 1× max. 10 ms [N] | 5× max. 10 ms [N] | Änderung | 1× Peak [N] | 5× Peak [N] |
|---|---:|---:|---:|---:|---:|
| right_front/left | 4.887 | 4.965 | +1.60 % | 5.161 | 5.401 |
| right_front/right | 4.506 | 4.699 | +4.28 % | 4.515 | 4.702 |
| right_rear/left | 5.160 | 5.151 | -0.17 % | 5.162 | 5.160 |
| right_rear/right | 4.559 | 4.564 | +0.10 % | 4.560 | 4.570 |

Die höchste einzelne Spitzenobergrenze steigt von 5,162 auf 5,401 N (etwa +4,6 %). Die längeren Lastplateaus liegen weiterhin bei ungefähr 4,0–4,2 N pro Backe. Fünffache Geschwindigkeit erzeugt in diesem langsamen, glatten Hub somit keine fünffache Kontaktlast. Ein historischer 1×-Lauf und ein neuer 5×-Lauf sind noch keine Wiederholstatistik.

![Kraftkurven gleicher Hubfortschritte](../../../setup/tasks/carton_speed5_20261117/comparison-final/forces.png)

## Bewegungs- und Physiknachweise

- Sollhub 147,8116949 mm; Sollzeit 56,5379733 → 11,3075947 s. Alle zwölf Tragegelenke gemeinsam: t/5, v×5, a×25, Ruck×125. Greif-/Einfahrbewegung und Haltezeit bleiben unverändert.
- Alle 2.263 kommandierten Gelenkpositionen stimmen mit der Referenz bis 1,70e−13 rad überein; größte v-/a-Skalierungsreste 1,37e−11 / 1,75e−9. Die tatsächlich beobachtete Ausgangsobjektpose weicht um 6,83 µm / 2,47e−5 rad ab.
- Gemessene maximale Armgeschwindigkeit 0,0114768 → 0,0575673 rad/s. Native Grenzen 0,04 / 0,065 rad/s werden in beiden Läufen nicht erreicht. Die alte native Begrenzung wurde an die bereits geprüften Gelenkgrenzen angebunden; Einzelgrenzen und Bremsreserve bleiben streng aktiv.
- Gleich: 0,5 kg, Reibung 0,6, Motormodell 30 Nm/rad / 0,7 Nm, Fingerdämpfung/Getriebe, Kollisionsgeometrie, Kinematik/Inertien, Physikschritt 0,5 ms sowie native Kontakt-/Kraft-/Engine-Binärdateien. Der Echtzeitfaktor beträgt 0,4 / 0,2: mehr Rechnerzeit pro Simulationssekunde, unveränderte simulierte Bewegung.
- Unabhängige Kraftaufzeichnung: 5.653 / 1.130 native Hubfenster, lückenlos. Quelluhr aus gemessenen Gelenken gegen Sollbahn ausgerichtet; 90%-Spannweite des Zeitfits 0,040 / 0,162 ms. Verglichen werden vollständige Fenster am gleichen gemessenen Hubfortschritt.
- Neuer 5×-Zyklus: DONE, Validierung und Kraftabdeckung PASS; tatsächlicher Schwerpunkt-Hub 147,738 mm, größter relativer Positionsfehler 0,373 mm. Vier Kontakte während des Tragens erhalten, unterstütztes Lösen beobachtet, abschließende Holds bestätigt. Eigene Welt/Runner/Recorder beendet; keine Hardwareaktion dieser Arbeit.

## Umfang und erhaltene Negativergebnisse

Die vollständige 90°-Bahn wird im konservativen 5×-Stoppreserve-Vorfilter abgewiesen (bis etwa 37 mm fehlende Reserve bei den geprüften Hüllgrenzen). Keine Lockerung. Deshalb wurde der geometrisch geprüfte vertikale Hub mit Rücksetzen isoliert. Die bisherige langsame Drehung stoppte bereits nahe 9°; dieser Bericht belegt keine vollständige beschleunigte Drehung und kein Absetzen in Seitenlage.

Versuche 01/03 stoppten vor Bewegung auf TASK RUNNER LOST. Lange native Interpolationskonvertierungen werden jetzt in 128-Segment-Blöcken exakt geprüft; keine Frist angehoben. Versuch 04 stoppte vor Hub bei einer 150,7-ms-Zustandslücke. Versuch 02 war wegen einer versehentlich unveränderten nativen 0,04-rad/s-Begrenzung **kein gültiger 5×-Vergleich**; Rohdaten und ausdrücklich zurückgezogener Vergleich01 bleiben als Diagnose erhalten. Erst Versuch05 liefert den hier verwendeten gültigen 5×-Zyklus. Vergleich02–04 sind Zwischenstände der Auswertung desselben gültigen Datensatzes; maßgeblich ist `comparison-final/result.json`.

Das Kartonmodell ist starr; es kann kein Quetschen oder Materialversagen vorhersagen. Die Betragsobergrenzen und beobachteten Einzelzyklen qualifizieren weder reale Kartonbelastbarkeit noch Hardwaregeschwindigkeit.

## Reproduktion und Artefakte

- 1×: `setup/tasks/carton_roll_contact_20261116_03/case00/run`.
- 5×: `setup/tasks/carton_speed5_20261117/fast-attempt05/case00/run`; Konfiguration `profile-5x-rtf02.yaml`, eingefrorene Quellen `frozen02/`.
- Versiegelter Vergleich: `setup/tasks/carton_speed5_20261117/comparison-final/result.json`; Kurven daneben. Auswertung `tools/compare_carton_lift_forces.py` ist ausschließlich lesend.
- 95 Task-Pythontests PASS; gezielte neue Blockpolynom-Regression gegen monolithische Polynome PASS. Lyrical-Taskbuild PASS. Logs: `setup/logs/uwa-carton-speed5-{tests,build}-final.log`.

Alle folgenden Pfade relativ zum Workspace, Standardumgebung zuerst laden:

```bash
source src/multi_arm_manipulation_UWA/scripts/env.bash
source setup/tasks/carton_speed5_20261117/frozen02/environment.bash
python3 src/multi_arm_manipulation_UWA/tools/compare_carton_lift_forces.py \
  --baseline setup/tasks/carton_roll_contact_20261116_03/case00/run \
  --fast setup/tasks/carton_speed5_20261117/fast-attempt05/case00/run \
  --output /tmp/carton-force-comparison-new
```
