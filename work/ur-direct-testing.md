# Direkte UR-Treiberbedienung ohne zusätzliche UWA-Sperren

- Status: **aktiv**.
- Datum: 2026-11-10, Australia/Perth.
- Nutzerkorrektur: zusätzliche GUI-/Adapter-Sicherheitsprüfungen entfernen,
  Bremsenlösen, Gelenkwinkel und Controllerwechsel auch über WLAN direkt testen.
  Native UR-Sicherheit und vorhandene Kollisionsalgorithmen nicht verändern.
- Bereiche: MATCH-Operationen, UWA-GUI/Tests, Bedienung/AGENTS/HANDOVER.
- Bereits laufende echte Treiber erhalten; keine realen Power/Brake/Play/
  Bewegungsbefehle durch den Agenten. Mock-Prüfung separat von Hardwaredomäne.
- Geplante GUI-Aktualisierung darf laufende Treiber nicht stillschweigend stoppen.
