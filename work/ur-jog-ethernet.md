# Ethernetbetrieb und manuelles UR-Jogging

- Status: **abgeschlossen** (Implementierung und Prüfungen; erster manueller
  physischer Jog-Versuch nach URCap-Portkorrektur offen).
- Datum: 2026-11-10, Australia/Perth.
- Nutzer: Kabel ersetzt, WLAN-Sonderbehandlung entfernen. Jogging aus MuR-GUI
  mit gleichem dezentralem Admittanzcontroller übernehmen, Nachgiebigkeit
  standardmäßig aus; zunächst hinten rechts testen.
- Bereiche: generische Jog-Helfer/MATCH-Adapter, UWA-Dialog/GUI, Inventar/
  aktive Netzwerkinformationen/Dokumentation/Tests. Historische Messdaten nicht
  als Ethernetmessung umdeuten. Laufende andere Aufgaben/Diffs erhalten.
- Keine ungerichtete automatische Realbewegung; manuelles Hold-to-jog mit
  Loslass-Stopp vorbereiten, Middleware/Controller über Mock prüfen.
- Ergebnis: gleicher MATCH-Regler/J-PARSE, MuR-Richtungshilfe geteilt;
  UWA-Jog-Dialog mit Translation/Rotation/Keyboard/Loslass-/Fokus-Stopp und
  kontrastreichem Feedback. Compliance aus, on_init-Preset durch Neuladen.
  Hardware66/Mock67 durchgängig getrennt; kein Idle-Twist beim Öffnen.
- Prüfungen: drei Pakete gebaut,19 gezielte UWA-/Adaptertests, acht MuR-
  Kartesiktests, Einzelarm-Live-Jog und Vierarm-GUI-Regression bestanden.
  Logs setup/logs/uwa-jog-*; installierte Startmenüaktion geöffnet und sichtbar.
  Ein vorhandener MiR-Fixture-Fehler im breiteren MuR-Test separat dokumentiert.
- Native Änderungen: nur verwaisten/unansprechbaren right_rear-Treiber nach
  bestätigtem STOPPED-Programm ersetzt; right_front/Simulation erhalten.
  Aktuelle echte JointStates und Compliance-Preset lesend bestätigt.
  Neue Jog-GUI geöffnet, Besitzerfenster erhalten. Keine realen Power/Brake/
  Play/Bewegungsbefehle. Nutzer muss URCap-Port50002 auf54002 korrigieren;
  IP192.168.8.209 korrekt, Ethernetping0,33ms/kein Verlust.
- Dauerhafte Details in HANDOVER.md und docs/ur_jogging.md.
