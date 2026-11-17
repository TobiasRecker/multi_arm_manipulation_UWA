# Kleiner realer Vierarm-Lauf mit Kollisionswächter

- Status: **realeVersucheabgeschlossen, vollständigerZielwegdurchGeschwindigkeits-
  wächterabgebrochen**, 2026-11-17 (Australia/Perth), Hauptagent.
- Abschluss17.11.: Alle4Greifer geöffnet/ParameterrückleseSPE16/FOR0bestätigt.
  RFq6Softwarehalt realbeobachtet; ursprüngliches50µradPrüfkriteriumunter
  Encoderrauschen, separateoffeneAnalyseHaltbestätigung0,699sinklRuhefenster.
  Originalfehlresultateerhalten. Watchdog-Anzeigeracekorrigiert, keineFristlockerung.
- VierArme realgleichzeitigbewegt (≥1,45s), Callbackmax37,236ms/100msBudget.
  Zielwegnichtvollständig: IstgeschwindigkeitLF0,004554rad/sgegen0,003Grenze,
  danachübrigeArmejeeigeneSpeedLimit-Verriegelung. Alle4Holds/Stillstandfrisch
  bestätigt, Wächterweiterarmed/keinResume. NächsterSchrittTracking-/Istgeschwindig-
  keitsabgleich, keine automatischeweitereFahrt. Quelle
  docs/hardware_commissioning_2026-11-17.md / setup/research/hardware-commissioning-20261117/.
- AbschließendeRegression153Motion-/24Greifer-Read-only-TestsPASS; ReportHTML/
  PNG-Messkurvengeprüft. KeinweitererrealerBefehl nötig; Hardware bleibt
  bewusstverriegelt. KeineoffeneBewegung/Testsitzung imHintergrund.

## Historische Vorbereitung und Durchführung

- Neuer Nutzerauftrag17.11.: Foto nach Wegstellen der Kiste erneut versuchen;
  bei nicht auswertbarem Bild99,1cm ausdrücklich übernehmen. Vollständiges
  Greiferöffnen prüfen und langsamen q1-/q6-Softwarestopp testen; danach kleiner
  Vierarmtest. Freigabe gilt diesem unbeladenen Test, nicht Kartongriff/CDF.
- Neues Foto20261117-101007-standard-37a99717: rechts24Ecken/2,050pxPrüf-RMS,
  links0Ecken/0Marker, daher autorisierten99,1cm-Fallback übernommen. Zentrales
  Layoutx±0,4955m, nurAbstand korrigiert; Y/Z/Winkelweiterhinvorläufig. Bestehende
  laufendeSimulationen nicht umgestellt/neugestartet. AltePläneinvalidieren.
- HeutigerStatus: alle4POWER_OFF/NORMAL, ProgrammeSTOPPED, keineTreiber/kein
  Hardwarewächter. Alle4GreiferserverGETerreichbar, ACT0/STA0/FLT0; POS3beiLF/LR/RF,
  POS230beiRR. UnaktivierteRegister sind noch kein Öffnungs-/Kraftnachweis.
- Eigenes hardware_commissioning.yaml fürunbeladenenq6-Test: vmax0,003rad/s,
  amax0,006rad/s²; unverändert40mmModellreserve,10Hz,200msFrische,1sangenommene
  Stopplatenz/0,2rad/s²angenommeneBremsung. Keine festeAbstandsschwelle gesenkt;
  begrenztereBewegung reduziert berechnetenStoppweg. VorRealbewegung vollständige
  Geometrie-/Istzustandsprüfung und heutigefreieBereiche/Not-Halt-Bereitschaft.
- Aktuelle Nutzerkorrektur: Greifer offen, physischer Abstand eher20cm;
  hintere Montagezentren mit Zollstock recht genau100cm. Ersetzt frühere
 30cm-/ungefähre100cm-Angaben. Keine Messunsicherheit des Zollstocks bestimmt.
  Bei sonst identischer Montage ergibt ursprüngliches offenes Mesh bei100cm
  Basisabstand ungefähr21cm Greiferabstand; damit plausibel konsistent.
- Nutzer schlägt vorhandene Tischboards/OAK zum Basisabgleich vor. Kamera-only-
  Prüfung über bestehende Foto-Lease; keine UR-Aktion/Dienstneustarts oder
  Profilaktivierung. Beide hinteren T_base_board-Matrizen liegen validiert vor,
  Frame ist jeweils base_link, Boardursprung OpenCV-Musterecke. Relative Kette:
  T_L_R = T_L_boardL inv(T_cam_boardL) T_cam_boardR inv(T_R_boardR).
  Keine OAK-Weltpose nötig, aber unveränderte Boardbefestigung/K/D erforderlich.
- Ergebnis Boardcheck: gespeicherte12.11.-PnP-Posen kombiniert mit akzeptierten
  Rear-Fits ergeben99,115cm Basisabstand. Historischer Plausibilitätscheck,
  keine aktuelle Genauigkeitsfreigabe (damaliger Fokus nicht protokolliert).
  Neue Standard-/HQ-Fotos16.11.15:46/15:48: linkesBoard nur1Marker/0Ecken,
  rechtes24Ecken, ausgeschlossene8Prüfecken1,835/1,924pxRMS >1px. Daher keine
  neue relative Basispose übernommen. Kamera geschlossen/Lease freigegeben.
 100zufällige starreTransformationsketten PASS; keine globaleKalibrierung,
  Schwellen-/Controller-/Roboteraktion. Nachweis docs/rear_base_spacing_review_2026-11-16.md
  und setup/research/four-arm-model-distance-review/board-base-review.json.
- Nutzer beauftragt reale kleine simultane Bewegung aller4URs auf vorgeprüftem
  kollisionsfreiem Weg, mit laufender Kollisionsvermeidung und Laufzeitmessung.
  Geometrie-/Takt-/Datenalterprüfung, keine absichtliche Kollisionsannäherung
  und keine vollständige reale Stoppreserveabnahme daraus ableiten.
- Bereiche: Hardware-Motion-Messdiagnostik, gezielter Testablauf/Artefakte,
  AGENTS/HANDOVER. Andere Greifpipeline läuft in Simulation und bleibt erhalten.
- Erster rein lesender Dashboardstatus: alle4POWER_OFF/NORMAL, ros.urp gestoppt,
  vorhandene Treiber lauschen, keine Reverse-Verbindung. Keine Schreibbefehle.
  Quelle setup/logs/uwa-four-arm-live-initial-status.json.
- Nächste Schritte: aktuelle RTDE-Gelenke lesen, vollständigen kleinen Vierarmweg
  prüfen und sichtbar dokumentieren; realen Monitor und Timing im Stillstand
  prüfen. Vor Einschalten/Bewegung aktuelle freie Bereiche/Not-Halt-Bereitschaft
  vor Ort klären. Keine gemeinsame Simulation/Hardwaretreiber neu starten.
- Nutzer bestätigt freie Bereiche/Not-Halt-Bereitschaft. Alle alten Armcontroller
  inaktiv nachgelesen, vier6Joint-CollisionHolds ausschließlichinaktiv geladen.
  Spätere Bringup-Abfrage meldet alle4bereitsROSREADY, keine Dashboard-
  Schreibbefehle oder Treiberstarts durch --apply (commands[]). Kein Fahrziel.
- Vorhandenen Monitor gezielt neu gestartet, weiterhin UWA_MOTION_ARMED=0.
  RR5.10 benötigt556ms zur RTDE-Protokollverhandlung. Separates2s-Anmeldefenster
  wie vorhandenerOutputReader, unveränderte200ms-Laufzeitfrische/Streamtimeout.
 121Paketchecks PASS. Alle4liefern jetzt frischeNativezustände. Neue
  Guard-Timingdiagnostik verändert keine Entscheidungs-/Schwellwertlogik.
- Geplanter Test +0,03rad im letzten Handgelenk aller4 ab tatsächlicher Pose
  abgelehnt: FCLkeineKollision/GelenkgrenzenPASS, aberhintereFingerhüllen nur
 42,3mm Abstand gegenüber172,9mm Planungsreserve. LiveSchwelle zuletzt155,8mm.
  KeineGrenze gelockert/keineFahrt/keinArming. OfflineSuche nur im letzten
  Handgelenk schafft keinen ausreichenden Start; nicht als Ausführungsplan nutzen.
- Reale15s-Stillstandmessung141GuardSamples: kompletterCallback median5,385ms,
  p9940,951ms/max54,486ms bei100msBudget. Taktmedian99,998ms/max102,888ms.
  Guard-Quell-Empfangsaltermax48,25ms, Supervisor-Guardaltermax146,43ms.
  Observer hattebis272,64ms Zustellalter: keine pauschale End-to-End-Fristgarantie.
- Bericht setup/research/four-arm-live-timing-20261116/report.html/result.json,
  Rohdaten setup/logs/uwa-four-arm-live-stationary-records.json. Aktuell alleURs
  ROSREADY, eigenerMonitor reinlesend. Aktive Stopp-/Bewegungsabnahme offen.
- Nutzer gefragt: zunächst separate Vorbereitungsfahrt planen(noch nicht
  ausführen) oder hintere Arme vorOrt weiter auseinander ausrichten. Nach
  Positionsänderung neu lesen/prüfen, keine gespeicherten Ziele blind übernehmen.
- Nutzerkorrektur: Arme seien real recht weit getrennt; bisherige Aufforderung
  zum Umstellen deshalb zurückgestellt.42,3mm ist ausschließlich modellierter
  Abstand zweier Fingerhüllkugeln, kein gemessener physischer Abstand. Quellen
  geprüft: hintereBasen im Modell90cm auseinander, Flansche43,7cm, Greifer
  nachinnenaufgleicherHöheca1,98m. Basis-/Tischposen undMontagewinkel bleiben
  nominale Annahmen; optische/FK-Kalibrierung hat diese nicht ersetzt.
- Vor weiterer Vorbereitung Modell gegen Aufbau prüfen, keine realen Arme
  passend zu fraglichen Modellannahmen umstellen. Visualisierung/Nachweis
  setup/research/four-arm-model-distance-review/{geometry.json,rear-envelope-gap.png}.
  Keine neue Geräteabfrage/Fahrt/Schwellwertänderung in diesem Klärungsschritt.
- Nutzer bestätigt Ausrichtung der hinteren Arme aufeinander, schätzt realen
  Greiferabstand aber auf etwa30cm. Als grobe Vor-Ort-Beobachtung festhalten,
  nicht als metrische Kalibrierung/Anlass für pauschales Verschieben der Tische.
  Basis-Mittelpunktabstand angefragt(Modell90cm); Öffnungs-/Kugelhülleneinfluss
  getrennt offline untersuchen. Keine erneute Aufforderung zum Umstellen.
- Nutzer ergänzt: Gazebo-Modell sehe passend aus, reale Montagezentren ungefähr
 100cm auseinander (weiterhin Schätzung). Laufendes normales Gazebo-Modell in
  Domain64 reinlesend abgeglichen: tatsächlich90cm, identisch zum Hardwaremodell;
  kein Beleg für einen unterschiedlichen Geometriequellstand. Snapshot
  setup/research/four-arm-model-distance-review/gazebo-bases.json.
- Öffnungs-/Hüllanalyse bei unveränderten90cm: Modellgreifer-Spaltprojektion
  offen11,03cm/geschlossen8,41cm, überÖffnungen8,35cm; Hardwarekugelhülle4,23cm.
  Kugelreserve erklärt einen Teil, aber nicht allein die grobe30cm-Beobachtung.
  Nicht die Tabellen global um10cm verschieben oder Schwellen senken, bevor
  Montage-/Werkzeugbezug metrisch geklärt ist. Keine Bewegung/Schreibaktion.
- Zusätzlicher geometrischer Gegencheck begrenzt den ursprünglichen Mesh-
  Oberflächenabstand bei90cm Basisabstand auf11,026–11,034cm(offen) bzw.
 8,406–8,414cm(geschlossen). Damit ist4,23cm ein zusätzlicher Hülleneffekt,
  aber die grobe30cm-Beobachtung noch nicht vollständig erklärt. Quellen
  setup/research/four-arm-model-distance-review/tool-distance-bounds.json.
  Nächster benötigter Realbezug: gemessener Montagezentren-Abstand und aktuelle
  Greiferöffnung; keine Freigabe allein aus den gerundeten100cm ableiten.
