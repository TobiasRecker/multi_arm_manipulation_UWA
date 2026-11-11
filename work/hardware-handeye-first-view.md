# Reale erste Aufnahmepose und Hand-Auge-Messreihe

- Status: **abgeschlossen – erste reale Reihe und Auswertung erfolgreich**.
- Abschluss:2026-11-11,15:43 Australia/Perth. Agent: Hauptaufgabe.
- Auftrag: nach erfolgreichem Front-Parken ausschließlich right_rear in erste
  Bildpose und durch die zuvor entwickelte Kalibrierreihe führen. Nutzer hat
  Erstpose und40 weitere Ansichten freigegeben; am11.11 Fortsetzung nach seiner
  Sicherheitsebenen-Anpassung, unveränderten Aufbau und freien Fahrraum bestätigt.
- Andere Arme nicht kommandiert. Front während der Aufnahme als reales festes
  Hindernis eingelesen; linke Arme laut Nutzer nominell Default Home.
- Erster Tag: Annäherung unterbrochen bei0,0331rad Restabweichung, erreichte
  ruhige Pose anhand echter Bilder übernommen. Shell-Fehlerfortsetzung und
  rclpy-Signalcleanup korrigiert; tatsächlicher Mock-Prozessgruppen-SIGINT
  bestätigt Cancel/Deaktivieren/Nachdrift0. Danach9 gute Bilder; native
  Sicherheitsebene/C400 bei Weg zu009, automatische Folge abgebrochen.
- Zweiter Tag: Nutzer behebt Sicherheitsebene. Nach Neustart Kamera/GUI/Treiber
  neu vorbereitet. Front zunächst Netzwerkproblem, später gleicheIP wieder da.
  Beide rechten Werkskinematiken aus Inventar und aktuelle reale Winkel verwendet.
- `resume-series` ergänzt: gültiges abgeschlossenes Präfix und Rollen erhalten,
 32 fehlende Originalziele aus aktuellen Zuständen neu planen/prüfen; vorhandene
  Bilder nicht überschreiben und per Hash binden.13 gezielte Tests bestanden.
- Resume-Fingerprint627571fd735af233510cdbc364a8d990fa46fdee6c874a3f5996af5889429f2b.
  Originale Ziele unverändert, gesamte Neuprüfung gut. Alle32 Ansichten ohne
  erneuten Sicherheitsstopp abgeschlossen, einschließlich bisheriger Stoppstelle009.
- Gesamtergebnis:41 unterschiedliche akzeptierte Bilder mit je24 Ecken,
 33 Fit/8 vorab festgelegte Prüfbilder, keine Ausreißer. Fokus404Manual,
 640×480,60000µs/Gain16. Stationäre aktualisierte HTTP-Bilder, ohne
  Sensor-Belichtungszeitstempel; nominelles K nur zur Planung, nicht zum Fit.
- Intrinsics PASS (Fit0,244px, Median Prüfung0,222px). Hand-Auge PASS:
  Median Prüf-Reprojektion0,466px, Boardpositions-RMS2,660mm, Rotation0,246°.
  Interne Validierung/Wiederholbarkeit, keine absolute Genauigkeitszusage;
  Bildränder außerhalb beobachteter Ecken noch nicht validiert.
- Rohdaten: setup/calibration/hardware_handeye/right_rear_20261110/.
  Versionierte Kopie samt Hashmanifest/Prüfgrafik:
  setup/calibration/hardware_handeye/right_rear_20261111/result_v1/.
  Ergebnisse aktiviert:false, keine TF-/Hardware-/Simulationsprofile geändert.
- Endzustand: Rear-scaled-JTC aktiv hält letzte Aufnahmepose, Front-Bewegungs-
  controller alle inaktiv. Zielabweichung Rear0,0000343rad; Front-Endvergleich
  zum Start0,0000472rad. Keine Rückfahrt oder weiteren Ziele.
- Eigene Domain68-Vorschau sauber geschlossen; UWA-Arms-GUI und beide rechten
  Treiber bleiben offen. completion_state.json gespeichert.
- Bereiche: uwa_cell_control Hardware-Aufnahme/Planung, MATCH-Ausführung,
  bildbasierter Solver unverändert wiederverwendet, Dokumentation/README.
  Simulationsbackend weiterhin getrennt. Logs setup/logs/uwa-handeye-resume-*.
- Dauerhafte Ergebnisse, Grenzen und nächster Einstieg stehen in HANDOVER.md
  sowie docs/hardware_handeye.md. Weitere Profilübernahme/Arme/OAK bleiben offen.
