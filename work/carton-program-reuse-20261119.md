# Wiederverwendbarer Kartongriff, 19.11.2026

- Status: abgeschlossen, 19.11.2026 (Australia/Perth). Nutzer möchte einen
  gespeicherten Ablauf, der denselben Karton bei veränderter Pose ohne
  Codeänderung greifen kann.
- Bereiche: versioniertes Kartonprogramm, Rezepterzeugung und gemeinsamer
  Ablauf für Offline-Planung und den bestehenden Motion-review-Piloten.
- Das Programm `carton-supported-v1` ist als JSON versioniert. Das erzeugte
  Rezept entspricht dem bisherigen Design. Beide Aufrufpfade kommen im Mock
  bis zum bestätigten Kontakt-HOLD. 48 gezielte Lyrical-Tests bestanden.
- Der dateibasierte Vergleich ergab mit derselben Programmversion, demselben
  Vierarmstart und demselben Modellprüfer zwei vollständige Parallelpläne.
  Der synthetische Versatz um 50 mm ging genau in beide Griffziele ein.
  Beide Mock-Stores anhand der erzeugten Bahnbündel befüllt und Status geprüft.
  Nachweis `setup/tasks/carton_program_reuse_20261119/comparison.json`.
- Betriebsübernahme am N100 und reale Prüfung des synthetischen Versatzfalls
  sind offen. Der lokale Vergleich endet nach dem Modellnachweis der offenen
  Einfahrt. Keine Gerätedienste, Kameras oder Roboter wurden dafür bedient.
