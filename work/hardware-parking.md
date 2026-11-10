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
- Parkskript/MATCH-Trajektorienausführung implementiert,23 gezielte Tests und
  Zwei-Paket-Build bestanden. Realweg mit aktuellen rechten Winkeln und linken
  Nutzer-Home-Posen geplant:620 Samples,61,81s, tool0~[.85,-.674,1.55]m.
  Isolierte RViz-Vorschau geöffnet; Nutzer hat Weg/freien Fahrraum ausdrücklich
  bestätigt und ersten Parkversuch freigegeben. Nur right_front führt nun den
  gespeicherten Plan aus, Ergebnis/Telemetrienachweis noch ausstehend.
- Erster Realversuch nativer Pfadtoleranzabbruch nach16,5s, tatsächlich keine
  relevante Gelenkbewegung (Front max0,000125rad). Keine Reverse-Verbindung
  nach Treiberneustart trotz DashboardPLAYING; keine native Programmflag-
  Nachricht empfangen (kein bestätigter false-Wert, GPIO publiziert Änderungen).
  Controller sauber inaktiv. Nutzer um frischen Stop→Play vorne rechts gebeten;
  weitere Fahrt erst bei wiederhergestellter Verbindung, gleicher freigegebener
  Weg und erneuter Start-/Kollisionsprüfung. Toleranzen nicht lockern.
- Nutzerkorrektur: linke Arme in nomineller Default-Home-Pose aufrecht;
  als user_nominal_home, nicht als gemessene Pendantwinkel verwenden.
  Vorne rechts laut Nutzer RUNNING und URCap .209:53002 eingerichtet.
- Diagnose: .103 Ethernet0,43ms/no loss und Reverse53001/53003/53004 verbunden.
  Alter ROS-Manager41381 liefert dennoch sechs Nullen. Unabhängiger RTDE-
  Ausgabeclient liest plausible actual_q beider rechter Arme (setup/logs/
  uwa-parking-{front,rear}-rtde.json). Rear-Manager inzwischen nicht mehr aktiv.
  Geplant: nur alten Front-Launch41338 nach Prüfung inaktiver Bewegung beenden,
  beide rechten Treiber in neuer GUI inaktiv starten; keine Power/Brake/Play/Fahrt.
