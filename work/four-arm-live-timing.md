# Kleiner realer Vierarm-Lauf mit Kollisionswächter

- Status: **Modell-/Realabgleich benötigt – Bewegung noch nicht ausgeführt**,
  2026-11-16 (Australia/Perth), Hauptagent dieses Chats.
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
