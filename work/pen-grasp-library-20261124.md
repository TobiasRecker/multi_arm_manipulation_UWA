# Stiftgriff als Library-Programm

- Status: Programm angelegt und aktuelle Plan-only-Prüfung abgeschlossen,
  24.11.2026 (Australia/Perth), Hauptagent. Reale Stiftaufnahme nicht ausgelöst.
- Auftrag: in Anlehnung an Supported carton grasp eigenes Programm für
  left_rear. OAK-Pro/OpenCV zuerst, Gemini-Fallback bei schwierigem Bild,
  aktuelle Objektpose, vollständige Planung, Greifen und vertikales Ausheben.
- Bereiche: eigener Wahrnehmungs-/Planungs-/Ausführungsrunner, Library-Katalog
  und Webansicht, neue Programmkonfiguration, gezielte Offline-/Mockprüfungen,
  Dokumentation. Bestehende Programme und Schutzbackend-Auswahl weiterverwenden.
- Nutzer hat30mm-Marker97 oben und96 seitlich am Stift/Adapter montiert,
  mittige Montage und vollständig eingesetzten Stift bestätigt und30mm
  schwarze Außenkante nachgemessen. Kappe für diesen CAD-Programmstand entfernt.
  Kamerasitzung und
  optische Pose getrennt von dieser Werkzeugbindung verwenden.
- Keine realen Ziele oder automatischer Programmstart bei Installation.
  Ausführung über konkrete Motion-/Kontaktprüfung wie beim Kartonprogramm.
  Keine Schutzdienstneustarts oder zusätzliche Laufzeitwächter geplant.

## Ergebnis

- **Pick pen from holder** mit Inspect pen, Plan pickup only und Start program.
  Aktiver Minimal-Katalog und drei Aktionen per HTTP geprüft; Quelle
  `setup/tasks/pen_pick_20261124/library-installed.json`. Lokales
  `uwa-minimal-power-gui.service` im Leerlauf neu geladen. Keine N100-
  Roboterdienste geändert. Direkter Oberflächenzugriff nicht verfügbar;
  keine tatsächlich ausgeführten GUI-Klicks behauptet.
- Frisches OAK-Pro-Bild mit bestätigtem Belichtungseinlauf; native Kanten-
  anpassung liefert in finaler aktueller Planung1,5335px RMS. Gemini-ROI-
  Fallback tatsächlich auf dem früheren dunklen Bild ausgeführt; Original-
  pixel im Ausschnitt erneut lokal gemessen. Modell-/Rückprojektionsfehler
  werden weiterhin abgewiesen; keine Gemini-Metrik als Roboterziel.
- Aktuelle Vierarmdaten und Kontext auf N100 gelesen, ganze Folge auf ROSmini
  geprüft: Anfahrt27,678s, vertikale Einfahrt8,069s, Lift8,069s;43,817s gesamt.
  Gelenkspitze höchstens0,1rad/s, Beschleunigung höchstens0,04070rad/s² in
  dieser Folge,83,3mm/s TCP-Limit. Keine zusätzlichen Temporeduzierungen.
- Grobe Sphärenkachelung am kleinen Halter ergab eine Überdeckung. Zusätzliche
  Offline-Szene enthält deshalb den ganzen Öffnungsbereich als konvexe
  Mesh-Sweeps mit analytischer Zwischenstützstelleninflation. Aktives Modell
  unverändert.376 unabhängige Öffnungszustände über8Körper lagen in den
  erzeugten Hüllen; normale Vollzell-/40mm-/Controllerinterpolantenprüfung
  bestanden. Nur vorgesehene Pad-/Adapter- und Führkontakte ausgenommen.
- Erfolgreicher Real-input-Plan ohne Arm-/Greiferbefehle:
  `setup/tasks/pen_pick_20261124/library-plan-current-02/`.
  Unabhängiger Nachweis `final-plan-validation.json` im selben Aufgabenstamm;
  portable RViz-Meshauflösung und Timeline ebenfalls geprüft.
- Ausführung nutzt SHA-gebundene Run-Helfer auf N100, bestehende Motion review
  und getrenntes Pen-Aufgabenvertrauen. Vor dem Schließen aktuelle Einfahr-
  aufnahme; kein automatisches Öffnen bei einem fehlgeschlagenen Griff.
- Reale Haltekraft, Montagegenauigkeit und Schreib-TCP bleiben ungeprüft.
  Nutzerfreigabe einer konkreten Fahrt erfolgt im Library-/Motion-review-Ablauf.
- Schlussprüfung:59 gezielte Tests bestanden, Python- und JavaScript-Syntax
  geprüft. N100 prüfte run-spezifisch Imports und alle drei eingefrorenen
  Plandateien erfolgreich, ohne ROS-Clients/Goals oder Greiferbefehle.
  Nachweise `targeted-tests.log` und `n100-import-and-files.json` im Aufgabenstamm.
  Die tatsächlich benötigten vier Plandateien werden übertragen; große lokale
  Analyse-/Sweep-Verzeichnisse bleiben auf ROSmini.
