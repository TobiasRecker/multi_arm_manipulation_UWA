# Allgemeine Überarbeitung der Stoppreserve

- Status: in Arbeit, 2026-11-17 (Australia/Perth), Hauptagent dieses Chats.
- Nutzer möchte nach72min vorgeschlagener Kalibrier-Anfahrt die Berechnung
  generell überarbeiten. Ursache: temporäre0,004rad/s-Kommandogrenze als Behelf
  gegen pauschale Reserve, alle Gelenke jedes Arms an Obergrenze und ein
  globales Maximum je Arm. Das ist keine physische UR-Leistungsgrenze.
- Während dieser Arbeit keine realen Fahr-/Power-/Brake-/Play-/Greiferaktionen.
  OAK-GUI, vier vorhandene Treiber und MONITOR-ONLY-Dienst erhalten.
- Bereiche: common.py/geometry.py/guard_core.py/planning.py/interlock.py,
  hardware_model.py, neue Rechenkern-/Regressionstests und Offlinevergleich.
  Laufende fremde hardware_state.py-/RT-Stopptest-/Teacheränderungen erhalten.
- Neuer Ansatz opt-in: einzeln überwachte Gelenkgrenzen, explizites
  Kommandotempo, Reserve pro Körper und Prüfung sämtlicher Kugelpaare;
  schlechteste Restreserve und kürzeste Ausfall-Lease getrennt bestimmen.
  Stillstehende physische Arme behalten positive überwachte Grenzen. Bereits
  vollständig eingeschlossene virtuelle Greiferöffnung nicht nochmals bewegen.
  Alte Profile/aktive Prozesse bleiben bei alter Rechnung. Modellreserve,
  Frische, angenommene Latenz/Bremsung nicht still verkleinern.
- Nachweis: analytische/randbasierte Rechentests, Signatur-/Frische-/Lease-
  Regressionen, bisherige Hardware-/Planungstests, vier reale eingefrorene
  Sichtwege offline vergleichen. Kein Stoppqualifikationsnachweis daraus ableiten.
