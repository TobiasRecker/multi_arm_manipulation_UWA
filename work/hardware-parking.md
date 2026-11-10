# Kollisionsgeprüfte Wartepose für Hardwarearme

- Status: **aktiv**.
- Datum: 2026-11-10, Australia/Perth.
- Nutzer bestätigt reale Jog-Bewegung right_rear. Neuer Auftrag: generisches
  Parkskript zur Vorbereitung der Kamerakalibrierung, zunächst right_front
  testen. Linke Arme laut Nutzer bereits manuell geparkt; deren Gelenkwinkel
  sind bislang nicht gemessen. Keine automatischen Befehle an linke/rear Arme.
- Bereiche: neues Plan-/Vorschau-/Ausführwerkzeug in uwa_cell_control bzw.
  wiederverwendbare Trajektorienausführung im MATCH-Adapter, Tests/Anleitung.
  Bestehende MoveIt-Zellgeometrie und Hardwareinventar verwenden. Simulation/
  Kalibrierbackend nicht auf Hardware umleiten. Aktuelle Fremddiffs erhalten.
- Zunächst lesend reale rechte Zustände/Controller prüfen; konkrete Parkpose
  und vollständigen Weg planen/visualisieren. Fehlende reale Hindernisposen
  und vorläufige Montagegeometrie sichtbar halten. Keine ungeprüfte Fahrt.
- Geplante Dienste: zunächst keine Neustarts, kein Power/Brake/Play.
