# Hydrogen Low für wiederholte Kartonerkennung

- Abgeschlossen am 20.11.2026, Australia/Perth. Hydrogen Low als Reserve
  in den lokalen Weblauf übernommen. ROSmini übernimmt die Bildaufbereitung,
  die Antwortprüfung und den vollständigen geometrischen Posefit.
- Die wiederverwendbaren Eingaben sind die feste Bildanweisung und ein
  zuletzt erfolgreiches Paar Suchfenster, gebunden an dieselbe
  ChArUco-Sitzung und einen ähnlichen Tischbildausschnitt. Der Ablauf
  aktualisiert die Fenster nach einem erfolgreichen Hydrogen-Fit.
- Freigabe auf ROSmini über `setup/skill_library/carton-hydrogen.enabled`.
  Der nächste Weblauf verwendet den aktualisierten Runner.
- Archivtest: Das Fehlerbild von 16:05 lieferte nach 34,74 s eine gültige
  Pose. Wiederverwendung auf der separaten 15:56-Aufnahme und beim erneuten
  16:05-Replay dauerte 10,63 bzw. 11,00 s. Eine weiter links stehende
  Lage und eine andere Kamerasitzung verwarfen den Cache. Offline-Bahnplan
  und lokale Vorbereitung der Übergabe bestanden. Reale Bewegung offen.
  [Messwerte](../../../setup/tasks/carton_hydrogen_fallback_20261120/measurements.json)
