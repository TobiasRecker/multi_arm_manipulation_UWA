# Bewegungsräume und Parallelität der Scanwege

- Status: **in Arbeit**, 2026-11-12, Hauptagent Digitalisierung.
- Nutzer möchte je Arm die maximale Annäherung/Überschreitung virtueller
  Trennebenen messen und daraus möglichst parallele Fahrten ableiten.
- Bereiche: neues Offline-Analysemodul, Tests, CLI und Bericht/Vorschau unter
  setup/digitization/. Bestehende Scanwege/Hardware-Controller nicht verändern.
- Vollständige URDF-Kollisionsgeometrie einschließlich Greifer/Kamera betrachten;
  TCP-/Endpunktprüfung reicht nicht. Anfangspositionen, Endlagen und alle Wege
  einschließlich Zwischenraum zwischen Prüfpunkten einbeziehen.
- Geprüfte Wege im kalibrierten Modell sind keine generelle reale Gefahrlosigkeit.
  Keine Fahrbefehle, keine Kamerazugriffe/Dienstneustarts; laufende LR-Reihe erhalten.
- Ziel: konkrete Paarberichte für den vorhandenen neuen-Karton-Scanplan,
  Unterscheidung zwischen Ebenenüberschreitung, überlappender konservativer
  Hülle und nachgewiesener Modelltrennung, anschließend Parallelgruppen ableiten.
