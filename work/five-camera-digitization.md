# Fünfkamera-Digitalisierung: erste Umsetzung

- Status: **in Arbeit**, 2026-11-12, Hauptagent Digitalisierung.
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
