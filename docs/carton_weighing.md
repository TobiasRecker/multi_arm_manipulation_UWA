# Kraftreferenz und20-mm-Wiegehub

Stand25.11.2026: Taskdateien auf N100 installiert, tatsächlicher Dateilader
und beide endlichen RTDE-Kraftrezepte geprüft. Die Library unter
`http://127.0.0.1:8780` verwendet jetzt `weigh_after_grasp: true`.
Noch kein abgeschlossener Wiegehub: Der Greifer-Parametrierungsblocker ist
mit einer Verbindung pro Auftrag behoben und über die normale ROS-Öffnung
beider rechter Greifer bestätigt. Der erste aktuelle Library-Lauf ist
gestartet; Details und Nachweise im aktuellen HANDOVER.
Keine Änderung an Schutzkern, Controllern, nativer UR-Sicherheit oder Payload.
Der unveränderte Schutzdienst wurde nach Routerunterbrechung und ausdrücklicher
Nutzerfreigabe im pausierten Leerlauf neu gestartet; frische Geometrie frei,
anschließend genehmigtes Resume mit vier bestätigten Controllern.

## Ablauf

1. Beide Kamerareferenzen und eine aktuelle Kartonpose verwenden. Anfahrt,
   Einfahrt und gemeinsamer20-mm-Hub werden vollständig vor der Anfahrt geprüft.
2. Die Variante `carton-supported-weigh-v1` greift20mm höher als der bisherige
   unterstützte Griff. Grund: Beim bisherigen Griff meldet das konservative
   Aufgabenmodell zuerst Kontakt mit inneren Greifergelenken. In der höheren
   Variante erfolgt der erste modellierte Schließkontakt an den Fingerpads.
   Das ist eine Offline-Entwurfsentscheidung, noch kein realer Griffnachweis.
3. Normale Motion Review für diese neue Greifhöhe anfordern. Nach der offenen
   Einfahrt ein frisches Foto prüfen. Die Kontaktfreigabe enthält ausdrücklich
   Schließen **und**20-mm-Hub; das alte Kontaktvertrauen wird nicht automatisch
   auf diese neue Bewegung übertragen.
4. Vor dem Schließen0,5s abwarten und beide UR-Kraftausgänge parallel für2s
   mit20Hz lesen. Software-Referenz speichern; kein `zero_ftsensor()` senden.
5. Beide Greifer regulär schließen. Nach0,5s ein weiteres2-s-Fenster mit noch
   tischgestütztem Karton aufnehmen.
6. Beide Arme mit einem gemeinsamen Zeitgesetz20mm vertikal anheben. Nach
   normalem Controllerabschluss0,5s abwarten, erneut2s messen und auswerten.
   Danach bleibt der Karton oben gegriffen. Kein automatisches Öffnen/Absenken.

Ein bereits geschlossener Griff liefert keine unbelastete Referenz. Für einen
neuen realen Versuch zunächst vor Ort die Tischauflage bestätigen und das
reguläre Öffnen/erneute Greifen beauftragen. Ein gespeicherter Offline-Start
ersetzt weder aktuelle Gelenkdaten noch die aktuelle Arbeitsbereichsfreigabe.

## Auswertung und Grenzen

`actual_TCP_force` liegt in UR-Basisorientierung vor. Die Kräfte beider Arme
in den gemeinsamen Weltframe drehen. Je Arm den Median der nach unten
wirkenden Kraft nach dem Hub minus dem Referenzmedian bestimmen. Die
vorzeichenrichtige Summe beider Lastanteile durch9,80665m/s² teilen. Keine
Beträge der Kraftvektoren addieren: Interne Klemmkräfte wären sonst Gewicht.
Keine gleichmäßige Lastverteilung voraussetzen. Den zusätzlichen Lastübergang
zwischen tischgestütztem Zustand und Hub separat ausgeben.

Die Library zeigt geschätzte Masse, beide vertikalen Lastanteile und die
Beurteilung `BOTH_ARMS_LOAD_PLAUSIBLE` oder `INCONCLUSIVE`. Positive Last muss
für beide Arme die beobachtete Streuung übersteigen. Das ist eine endliche
Aufgabenbeobachtung, kein Kraft-/Schlupfwächter und kein Nachweis aller vier
Pads oder vollständiger Freiheit von Fremdkontakt. Keine globale Pause oder
Greiferaktion aus dem Messergebnis ableiten. Nach einem Messfehler wird ein
bereits abgeschlossener Hub nicht wiederholt; fehlende Messung klar melden.

UR nennt für UR5e±4N Kraftgenauigkeit je Sensor. Eine gespeicherte Referenz
kann konstante Offsets reduzieren, belegt aber keine genaue Waage. Die
angegebene5–95%-Messstreuung und das daraus abgeleitete empirische Masseband
sind **kein absolutes Genauigkeits- oder Konfidenzintervall**. Payload,
Schwerpunkt und TCP-Offset müssen zwischen den Fenstern unverändert bleiben;
sonst wird keine gültige Differenzmasse ausgegeben. Nutzerangabe: leerer
Karton, geschätzt500g bis1kg, keine präzise Waage. Diese Schätzung ist weder
Referenzmessung noch Akzeptanzgrenze.

Quellen: [UR-Gewichtsermittlung](https://www.universal-robots.com/articles/ur/programming/weight-detection-of-any-picked-object-using-e-series-robot/),
[UR-RTDE-Ausgänge](https://docs.universal-robots.com/tutorials/communication-protocol-tutorials/rtde-guide.html),
[UR5e-Datenblatt](https://www.universal-robots.com/manuals/EN/TechSheets/UR5e_techsheet_pdf_online/UR5e_techsheet_en.pdf).

## Offline-Nachweis

`setup/tasks/carton-weigh-20261125/complete-plan/` verwendet ausschließlich
Archivdaten vom erfolgreichen24.-November-Lauf als Planungsfall, keinen als
aktuell ausgegebenen Hardwarezustand. Gesamte Folge erfolgreich geprüft;
Hub1,149305077s bei unveränderten0,1rad/s,0,2rad/s² und83,33mm/s TCP.
Die kurze Bewegung wird durch die Beschleunigungsgrenze bestimmt. Primäre
volle Greiferöffnungshüllen und40-mm-Nachbararmmarge bleiben unverändert.

Das getrennte Aufgabenmodell verwendet den ersten nominellen Padkontakt auf
der bestehenden konservativen Kartonhülle. Der so bestimmte Greifergelenkwinkel
ist keine gemessene Öffnung und wird nicht als Fingerbefehl gesendet. Nur
beabsichtigte Fingerpad-/Kartonkontakte sind ausgenommen; innere Greifergelenke
bleiben geprüft. Der anfangs5mm unter die Tischfläche erweiterte Modellboden
bewegt sich monoton von den koplanaren Tischen weg; nach dem Hub15mm Abstand
zur Hülle. Die zeitparametrierten Controllerpolynome werden mit bewegtem
Karton an257 Stützstellen geprüft. Reale Kontaktsteifigkeit, Belastbarkeit und
mechanisch exakt gleicher Fortschritt beider Arme sind dadurch nicht bewiesen.

Pfade und Hashes des Wiegeplans werden zusammen mit Anfahrt/Einfahrt für den
Executor umgeschrieben. `staged/` und `staging.log` belegen diesen lokalen
Transferaufbau. `executor-files-local.log` prüft den Ausführungslader rein
an Dateien auf ROSmini; dies ist kein N100-Lauf. Messfenster und Resultate
werden bei realer Ausführung im jeweiligen Zyklus unter `force-reference/`,
`force-supported/` und `weighing/` gespeichert.
