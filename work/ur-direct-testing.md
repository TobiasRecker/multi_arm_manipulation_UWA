# Direkte UR-Treiberbedienung ohne zusätzliche UWA-Sperren

- Status: **abgeschlossen**.
- Datum: 2026-11-10, Australia/Perth.
- Nutzerkorrektur: zusätzliche GUI-/Adapter-Sicherheitsprüfungen entfernen,
  Bremsenlösen, Gelenkwinkel und Controllerwechsel auch über WLAN direkt testen.
  Native UR-Sicherheit und vorhandene Kollisionsalgorithmen nicht verändern.
- Bereiche: MATCH-Operationen, UWA-GUI/Tests, Bedienung/AGENTS/HANDOVER.
- Bereits laufende echte Treiber erhalten; keine realen Power/Brake/Play/
  Bewegungsbefehle durch den Agenten. Mock-Prüfung separat von Hardwaredomäne.
- Geplante GUI-Aktualisierung darf laufende Treiber nicht stillschweigend stoppen.

- Entfernt: zusätzliche Dashboard-/Programmpfad-/Inaktivitäts-/Armzahl-/
  Aktivarmzählungs-/Aktivierungslock-/GUI-Besitz-/rqt-Freigabe-Gates. Status rein
  informativ, direkter Aufruf bestehender UR-Helfer/Controller-Services.
- Gelenkwinkel-Leser/GUI-Tab ergänzt, Broadcaster-/Controller-Nachladefunktion
  ergänzt. Bereits aktive Broadcaster bleiben erhalten, vorhandene konfigurierte
  Bewegungscontroller werden nicht deaktiviert. Neuer Spawner wartet länger.
- 14 Offline-Tests, zwei Pakete gebaut, isolierte Live-Mock-Integration bestanden:
  direkte Ein-/Zwei-/Vierarm-Switches ohne Dashboard, 24 Gelenke, fehlenden
  Controller nachgeladen, wiederholtes Laden idempotent, Admittanz/Stopp/Abbau.
  Logs setup/logs/uwa-direct-{tests,build,live}.log, finaler JSON unter
  setup/logs/uwa-control/mock-gui-validation.json.
- Lesender Hardwareversuch8s ohne JointState. Log belegt frühe Spawner-Fehler
  und Netzwerk-/RTDE-Abbrüche; echte Winkel noch nicht erfolgreich empfangen.
- Neues Fenster UWA · Direkter UR-Test (Hardware/rear-right) über installierte
  Desktop-Aktion geöffnet, Fenstertitel/PID bestätigt. Altes Besitzerfenster
  und beide Hardware-Launch-PIDs41338/41339 erhalten; keine realen Power/Brake/
  Play-/Bewegungsbefehle gesendet. Altes Besitzerfenster nicht zum GUI-Update
  geschlossen, weil dies seine Hardwaretreiber beenden würde.
- Native UR-/Treiberfunktionen, bestehende Regler-/Kollisionsalgorithmen erhalten;
  Kollisionsoption in UWA-Profilen weiterhin deaktiviert, nicht als aktiv behaupten.
  AGENTS/HANDOVER/Bedienung in beiden Repos aktualisiert.
