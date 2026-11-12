# Fünfkamera-Digitalisierung: erste Umsetzung

- Status: **erste Softwarestufe abgeschlossen; reale Scan-Fahrt offen**, 2026-11-12, Hauptagent Digitalisierung.
- Nutzer hat den Beginn des vorgeschlagenen Ausbaus beauftragt. Aufnahme mit vier
  Wrist-Kameras plus OAK, gemeinsame Zielansichten und kleine Zusatzansichten.
- Bereiche: neues Modul object_scan_plan.py; kleine parametrisierende Erweiterung
  board_capture.py / board_capture_gui.py, eigene Scan-Konfig,
  CLI und gezielte Offline-Tests. Bestehende Kamera-Worker/LED-Steuerung und aktive
  Kalibrierreihen bleiben bei den anderen Aufgaben. Gemeinsame CaptureRig-Bereiche
  nur bei notwendiger kleiner Erweiterung, bestehende GUI bleibt kompatibel.
- Keine Dienste neu starten; keine Aufnahmen während fremder Kameraserien.
  Zunächst Offline-Planung gegen vollständiges Modell. Keine neue reale Armfahrt
  ohne konkrete geprüfte und durchsehbare Wege; keine implizite Power/Brake/Play.
- Ziel dieser Umsetzung: wiederverwendbarer Fünfkamera-Aufnahmepfad und konkreter
  Sicht-/Erreichbarkeitsbericht für einen gemeinsamen Objektbereich. Danach neue
  Wege in RViz prüfen; Rekonstruktionsbackends separat am eingefrorenen Datensatz.

- Nutzerkorrektur: neuer größerer Karton **zwischen beiden Tischen**, nicht der
  frühere Karton auf dem rechten Tisch. Erste plan_v2 mit 20 Modellansichten
  bleibt als verworfener Aufbau archiviert; keine Fahrfreigabe daraus ableiten.
  Maße/Auflagehöhe angefragt; zunächst OAK-Einzelfoto ohne Wrist-/Armzugriff.

## Umgesetzter Stand

- OAK-first-Bootstrap mit Originalhash, tatsächlichem Fokus, Board-PnP,
  assistiertem geometrischem Fit und getrennten Planungsreserven. Neues reales
  Foto aufgenommen, grob44×35×16cm statt Nutzerstartwert40×30×20cm.
- Fünfkamera-GUI/CLI, beide Boardidentitäten, kontinuierlicher Telemetrieaudit;
  Dreikamera-Standard erhalten. Objekt-Planer rein lesend/offline, alle Wege
  zeitparametriert und voll geprüft, keine Ausführungs-Clients.
- Erweiterter Suchbereich für neuen Karton fand20Modellansichten/19Wege,
  2108Prüfpunkte. Neuere Zustandsplanung wird separat berechnet.
- Metrische Vorbereitung verallgemeinert, beobachtete OAK-Boardbrücke mit
  geprüfter Richtung. Fehlende K/D nicht ersetzt. Noch kein realer Fünfersatz.
- Build und30gezielte Tests PASS, echte reine4Arm-Telemetrieprobe PASS;
  Qt-Fünferansicht offline mit synthetischen Snapshots geprüft.
- docs/object_scan.md, README/AGENTS/HANDOVER parallel aktualisiert.

## Abschluss dieser Softwarestufe

- Neue reine Live-Lesung18:35:48AWST und konkrete Planung im aktuellen Profil:
  new_carton_plan_current/,20Ansichten/19Wege/1963Prüfpunkte,139s+55sreineFahrt.
  Alle Ergebnisdateien ausdrücklich nicht ausführbar; keine neue reale Armfahrt.
- OAK-Overlay, konservative geometrische Skizze und englische Qt-Oberfläche
  visuell geprüft. GUI-Testbilder deutlich als synthetische Snapshots markiert.
- Installierte CLI-Einstiege funktionieren, Build PASS,35gezielte Tests PASS,
  shellsyntax/diff-whitespace geprüft. UrsprünglicherDreikameraablauf bleibt.
- Reale Fünferaufnahme/Wegeprüfung am Aufbau erst nach freien Kameras/Armen und
  konkreter Routendurchsicht. NativeHD-Profile teilweise separat/inArbeit.
  Noch keine automatische Segmentierung und kein neuronales Mesh für neuenKarton.
