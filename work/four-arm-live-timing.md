# Kleiner realer Vierarm-Lauf mit Kollisionswächter

- Status: **in Vorbereitung**, 2026-11-16 (Australia/Perth), Hauptagent dieses Chats.
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
