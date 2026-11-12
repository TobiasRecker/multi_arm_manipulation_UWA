# Bewegungsräume und Parallelität der Scanwege

- Status: **abgeschlossen – Offline-Analyse und paralleler Prüfablauf**, 2026-11-12, Hauptagent Digitalisierung.
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

## Ergebnis

- Alle68Kollisionskörper, Originalquintiken und Zwischenpunktgrenzen analysiert.
  Fünf Paarungen bleiben in Basisrichtung getrennt; hinteres Paar überschreitet
  mittige Wände um bis34,1/60,4mm (nach außen gerundete obere Schranken).
- Anfangswege aller4Arme trotz dieser Übertritte über räumliche Ebene getrennt,
  kleinster Nachweis28,6mm. Zusatzansichten hinten nicht mit20mm nachgewiesen;
  auch289Einzelkörperpaare geprüft, linke Finger/rechteswrist_2 bleiben offen.
- Parallel-Prüfplan: alle4initial, dannLF/LR/RFextras parallel, dannRRextras.
  Originalpunkte/ungeklärteLR→RR-Reihenfolge erhalten, Stillstandsbarrieren.
  Reine Fahrzeit193,5→80,9s; weiterhin executable:false, keine Armkommandos.
- CLI/Tests und Bericht/Vorschau erstellt. Erstes dichtes Optimierungsproblem
  war ungeeignet (Speicherbedarf); durch fünfvariable lineare Stützebenen-
  Suche ersetzt, tatsächliche vollständige Stützabstände bleiben maßgeblich.
  Ursprüngliche Fehlversuchslogs erhalten. Kein fremder Prozess angehalten.
- Scan-RViz-Domain auf74 korrigiert, da LR-Kalibriervorschau Domain73 verwendet.
  Keine Instanz geöffnet/neu gestartet; nur eigener Quellaufruf/Dokumentation.
- README/AGENTS/HANDOVER/docs/scan_separation.md aktualisiert.

## Prüfnachweis

- Build PASS,12neue Tests plus9Planungs-/Parkregressionen:21PASS.
- InstallierterCLI vollständig am realen gespeicherten Scanplan durchgelaufen;
  Grenzen, Gruppen und Zeitplan exakt identisch zur vorherigen Auswertung.
  separation_installed/ dokumentiert den regulärenAufruf. CLI --help geprüft.
- Finale separation_review/ enthält Bericht, JSON, nichtausführbarenParallelplan
  und visuell geprüfteXY-Grafik. Zahlenobergrenzen nachaußen gerundet.
- Keine Arm-/Kamera-/Controller-/Treiberbefehle und keine Safety-/Kollisions-
  Freigaben geändert. Geometrienachweis nur für diese Wege/im frozenModell;
  aktuelle reale Starts/Umgebung und konkrete Route bleiben vorFahrt zu prüfen.
