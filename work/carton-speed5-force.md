# Kraftvergleich desselben Ablaufs bei1× und5×

- Status: in Arbeit, 2026-11-17 (Australia/Perth), Codex dieses Chats.
- Auftrag: simulierte Kontaktkräfte bei fünffacher Robotergeschwindigkeit
  vergleichen, gleiche Bahn/Mechanik; tatsächliche Physik statt schnelleremReplay.
- Bezug: geplantes90°-Drehrezept. Noch kein vollständiger Kontaktzyklus, daher
  Abbrüche erhalten. Hardware und fremde Simulationen unangetastet.
- Vorprüfung: globale konservative Hüllreserve auch mit realistischen proDOF-
  Geschwindigkeitsmaxima reicht für vollständige5×-Drehung nicht (bis37mmFehlreserve).
  Kein Abschalten. Messbare Teilprüfung: identischer147,55mmHub und Rücksetzen
  bei1×/5×, ohneDrehung; vollständigeDrehung getrennt als nicht freigegeben melden.
- Zeitkompression für alle12Tragegelenke gemeinsam: t/5,v×5,a×25,jerk×125.
  Greif-/Einfahrbewegung, Masse/Reibung/Preload/Physikschritt gleich. Strikte
  perGelenk-Grenzen samt vollständigerStoppreserve werden vorab gebunden.
- Bereiche: optionale Skalierung/Explorationsdaten imTaskpaket, Tests, eigene
  Vergleichsskripte/Artefakte/Docs. Aktive Offline-Zielkandidatenarbeit erhalten.
