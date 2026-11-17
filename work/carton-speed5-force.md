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

## Umsetzung und erste Messung

- Optionale `carrying_speed_multiplier` skaliert alle12Gelenke und Objektposen
  gemeinsam in der Zeit. Positionen bleiben bytegleich; tatsächliche JTC-
  Polynomextrema für Geschwindigkeit/Beschleunigung sowie Ruckgrenze geprüft.
- Explizite `joint_velocity_overrides_rad_s` nur für die12rechten Armgelenke,
  vollständig in strikter Laufzeitprüfung und geometrischem Bremsbudget.
  Finger-/Fremdarmgrenzen bleiben erhalten. Vergleichs-Hubprofil trägt bis
 147,8116949mm, ohneDrehung, mit vollständigem Vorabzeugen für Hub/Rücksetzen.
- Tests70Pythonfälle PASS einschließlich vorhandener Hardwarevorbereitungstests;
  Lyrical-Paketbuild PASS. Erster Testaufruf vorNeuinstallation hatte alte
  installiertePythonmodule, Importfehler erhalten; nachBuild alle70PASS.
- 1×-Kontrolle: vorhandener vollständiger Hub aus
  carton_roll_contact_20261116_03/case00/run, exakt56,5379733s Sollzeit;
  Auswerteuhr aus gemessenen Gelenken gegen geprüfte Bahn bestimmt,
  90%-Spannweite nur39,6µs,5653native Kraftfenster ohneLücke imHub.
- Neue5×-Bahn:11,3075947sHub und Rücksetzen, maxJTC0,057385rad/s und
 0,015983rad/s². Gleiche500g/Reibung0,6/Motor30Nm/rad0,7Nm/Physik0,5ms.
  Gemeinsame proGelenk-Hüllreserve imHubvorfilter mindestens17,77mm.
- fast-attempt01 vorBewegung mit TASK RUNNER LOST währendPlanreview gestoppt;
  beideHolds bestätigt, unterstützt. Keine5×-Kraftmessung daraus ableiten.
  Wiederholung fast-attempt02 mit unveränderten Parametern aktiv; Bild-, Plan-
  und Ausrichtungsreviews jeweils explizit durchgeführt. Quellen bleiben stabil.
