# Stoppreserve nach Körper und Gelenk

Stand17.11.2026. Neuer ausdrücklich wählbarer Modus
`per_body_joint_caps_v2` für Planung und Wächter. Vorhandene Profile bleiben
bei der bisherigen Rechnung. Keine reale Fahrt oder Dienstumschaltung wurde
durch diese Überarbeitung ausgelöst.

## Ursache der72Minuten

Die temporäre Ausweichkonfiguration begrenzte alle Kommandos auf0,004rad/s
beziehungsweise0,229°/s, damit die pauschale Reserve in den vorhandenen Abstand
passt. Das war als allgemeine Lösung unzweckmäßig. Links vorne muss das
langsamste Gelenk146,28° beziehungsweise2,553rad fahren. Für die vorhandene
glatte Quintik mit Ruhe an beiden Enden gilt
`T >= 1,875 * größter_Gelenkweg / maximale_Geschwindigkeit`.
Damit entstehen1196,75s beziehungsweise19,95min. Alle vier seriellen Wege
ergeben4331,70s beziehungsweise72,19min. Das ist keine UR-Leistungsgrenze.

Die bisherige Reserve setzt alle Gelenke jedes Arms gleichzeitig an ihre
Obergrenze, einschließlich stillstehender Arme. Das größte Ergebnis über den
ganzen Arm wird für jedes Körperpaar verwendet. So blockiert die pauschale
Reserve auch geometrisch freie Wege.

## Neue Rechnung

- Gewünschtes `command_velocity_limit_rad_s` und sechs einzeln überwachte
  `joint_velocity_limits_rad_s` je Arm werden getrennt gespeichert. Reihenfolge:
  Schulterpan, Schulterlift, Ellbogen, Wrist1/2/3. Auch unbeteiligte Arme brauchen
  ausdrücklich positive Grenzen; ein Messwert null ist keine Zukunftszusage.
- Jeder Kollisionskörper erhält seine eigene Bewegungs-/Bremsdistanz aus
  analytischen Hebelarmgrenzen. Eine momentane Jacobimatrix oder ein günstiges
  Geschwindigkeitsvorzeichen wird nicht als zukünftige Schranke verwendet.
- Sämtliche Kugelpaare bleiben geprüft. Maßgeblich ist die kleinste Restreserve
  `Oberflächenabstand - Modellpuffer - KörperreserveA - KörperreserveB`.
  Das kritischste Paar kann ein anderes sein als das geometrisch nächste.
  Beide Angaben bleiben sichtbar.
- Die erlaubte Zeit seit der letzten Prüfung wird ebenfalls über alle Paare
  minimiert. Das zeitkritische Paar kann vom distanzkritischen Paar abweichen.
  Fehlende/ungültige neue Lease-Angaben führen zum Stopp.
- Ein bereits vollständig eingeschlossener Hardware-Greiferöffnungssweep wird
  nicht nochmals durch Bewegung seines virtuellen Öffnungsgelenks aufgebläht.
  Das gilt nur mit dieser geometrischen Zusicherung und festem Modellkoordinaten-
  null. Physische Armgelenke und alle Werkzeugkörper bleiben berücksichtigt.
- Planung und Ausführung verwenden dieselben Achsgrenzen und ein gemeinsames
  Zeitgesetz. Eine langsame Achse mit winzigem Weg drosselt nicht pauschal alle.

Die Körperreserve bleibt
`D = sum(r_j*v_j)*(Datenalter + Prüftakt + Stoppannahme)`
`    + sum(r_j*v_j²/(2*Bremsannahme))`.
`v_j` umfasst mindestens die einzelne überwachte Grenze samt akzeptierter5%-
Toleranz; höhere gemessene Werte vergrößern die Rechnung und lösen den
Geschwindigkeitsfehler aus. Hüllenradien sind im Oberflächenabstand abgezogen.

## Vergleich derselben vier Wege

Unverändert: Modelle/Wege/Öffnungshüllen,4cmModellpuffer,10Hz,200msFrische,
1sangenommene Reaktion und0,2rad/s²angenommene Bremsung.

| Arm | Temporärer alter Plan | Neuer Offlineplan |
| --- | ---: | ---: |
| left_front |19,95min |1,60min |
| left_rear |16,26min |4,77min |
| right_rear |23,69min |1,89min |
| right_front |12,31min |0,98min |
| Summe seriell |72,19min |9,24min |

Kommandotempo höchstens0,05rad/s, links hinten wegen geringer Reserve nur
0,01364rad/s. Unbeteiligte Achsen erhalten hier0,001rad/s, bewegte Achsen eine
Trackingzulage0,002rad/s plus1,3mal geplanter Achsspitze. Diese Betriebsverträge
sind Vorschläge, keine gemessene physische Tracking-/Stoppqualifikation.

Das Audit zieht zwischen Abtastpunkten analytische Körperbewegung ab und prüft
Timing, FCL und neue Reserven erneut. Alle Phasenprofile und ihr Modell-/
Grenzenhash bleiben getrennt. Es gibt keinen Roboter-/Dienstzugriff:

```bash
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
python3 src/multi_arm_manipulation_UWA/tools/audit_stopping_reserve.py \
  --plans /absolut/phase1-plan.json /absolut/phase2-plan.json \
  --output /absolut/neues-audit-verzeichnis
```

Resultat: `setup/calibration/oak_recalibration_20261117/reserve-v2-audit-02/summary.json`.
Erster Auditversuch mit relativem Xacro-Pfad blieb als Fehler erhalten.

## Verwendung und Grenzen

Neues Profil: `stopping_reserve_model: per_body_joint_caps_v2`, komplette
Gelenkgrenzenmatrix und Kommandotempo. Fehlende Arme/Gelenke, null, negative/
nichtendliche Grenzen, unbekannte Modelle und gleichzeitige alte Armgrenzen
werden abgewiesen. Modus/Grenzen/Kommandotempo sind signaturgebunden. Alle
Wächter-/Supervisor-/Watchdog-/Planungsprozesse müssen dasselbe Profil nutzen.
Phasenprofile wechseln nicht automatisch während laufender Bewegung.

Die native RRT-Vorsuche verwendet weiterhin konservative Arm-Maxima; direkte
Verbindungen, Python-Endprüfung und Laufzeit verwenden die Körperrechnung.
Die Vorsuche kann dadurch unnötig scheitern; kein ungeprüfter Fallback.

Stoppzeit/Bremsung bleiben unqualifizierte Annahmen. UR veröffentlicht modell-,
Geschwindigkeits- und lastabhängige Stoppkurven; sie ersetzen keine Messung der
eigenen PC-/Netzwerk-/Controllerkette.
[UR5e-Herstellerangaben](https://www.universal-robots.com/manuals/EN/HTML/SW10_15/Content/prod-usr-man/complianceUR5e/H_g5_sections/stopping_time_n_distances_g5/stoppingTimeAndDistance_en_g5_1.htm).
Vor realer Verwendung sind frische Startzustände und der aktive Profil-/
Modellnachweis erforderlich. Der Vergleich garantiert keine reale Fahrzeit.

Der erste Mock-Test bestätigte Stoppfälle, scheiterte aber an einer Testannahme:
ein legitimer Teilreset wurde als vollständiger Reset erwartet. Nur die
Fake-Testvorbereitung stellt nun nach erneut stabilen Voraussetzungen eine
weitere explizite Anfrage. Produktives Resetverhalten und Frische bleiben gleich;
das Fehlerresultat wurde erhalten.
