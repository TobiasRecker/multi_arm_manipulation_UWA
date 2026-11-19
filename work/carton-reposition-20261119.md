# Karton loslassen und Home,19.11.2026

- Status: aktiv, Hauptagent dieses Kartonchats; reale rechte Arme exklusiv auf N100.
- Nutzer bestätigt Griff, bezeichnet bisherigen Zeitlauf als nicht repräsentativ.
  Neuer Auftrag: aufliegenden Karton loslassen, nach oben freifahren, beide
  rechten Arme Home; anschließend wartet das System, Nutzer stellt Karton um.
  Keine neue Greifsequenz starten, bis Nutzer die Umstellung bestätigt.
- Anfang: beide rechten OBJ2, virtuelle Objektgruppe HOLD-only. Erst beide
  nachgewiesen offen/ohne Kontakt, dann unbeladene Armziele. Bestehende
  0,1rad/s,0,2rad/s²/40mm, Trendruhe und Frische-/nativeStopps unverändert.
- Ergebnisse N100 `setup/tasks/carton_reposition_20261119/`; aktuelle Objektpose
  aus letzter unverändert gehaltener realer Einfahrt. Nach Benutzerumstellung
  diese Pose nicht weiter als aktuelle Zielpose verwenden.

## Karton für Umstellen freigeben,19.11.2026

- Nutzer bestätigt Griff, möchte repräsentativen neuen Versuch mit umgestelltem
  Karton. Aktueller Auftrag ausschließlich: lösen, hochfahren, Home, danach warten.
- Beide rechten Greifer tatsächlich geöffnet: OBJ3/POS3/PRE0/FOR0/SPE16,
  remaining_contact_members[]. Releasebericht bewahrt kurzen Halte-Transienten
  (`HELD_OPEN_UNCONFIRMED`); keine Wiederholung des Fingerziels. Frischer
  Offen-/Armzustand aufgenommen; Rückzug/Home mit vorhandenen vollständigen
  Vorfahrprüfungen in Arbeit. Keine geladene unabhängige Bewegung.
- Reale Betriebsdienste weiter ausschließlich N100. Laufende Ergebnisse
  `setup/tasks/carton_reposition_20261119/`, Arbeitsstand
  `src/multi_arm_manipulation_UWA/work/carton-reposition-20261119.md`.
- Vorherige Kontakt-HOLD-Aussagen unten historisch. Nach Home keine erneute
  Greifsequenz; erst Nutzerumstellung abwarten und neue Kartonpose bestimmen.


- Loslassen beideOBJ3/POS3/PRE0 tatsächlich, keineKontaktmitglieder. Der
  Releasebericht enthält kurzen `Arms not all resource-held`-Transienten;
  Fehler erhalten, Fingerziel nicht wiederholt. Frischer Offen-/Ruhesnapshot,
  danach Rückzug vollständigPASS (`retreat/result.json`), beide150mmhoch.
- ErsterHomeplanvollständiggültig, realeRF-Fahrt durch `Device epoch changed`
  abgebrochen. Fehlerpfad bestätigt alle4Resourceholds/Latches, keineNative-
  Stop-Anforderung nötig. Ursache der generischen Zeitdiagnose noch nicht
  genauer belegt; keine Zeit-/Frischegrenze verändert. Neu gemessene Positionen
  (`home-replan-snapshot`) und komplett neuer Homeplan, keine Wiederverwendung
  desabgebrochenen Starts. Eigener Task ohneCPUQuota, CPUWeight200; keine
  Änderung derWächter/UR-Dienste oderphysischerGeschwindigkeiten. NeueFahrt
  `home-replanned/` läuft; Ergebnisse erstnachEndhaltbehaupten.
