# Langsamer Kartongriff in der echten Zelle

- Status: **bereit für Live-Inbetriebnahme; automatischer Realgriff noch offen**,
  2026-11-16 (Australia/Perth), Hauptagent dieses Chats.
- Nutzerauftrag: bestehenden Zweiarm-Kartonablauf zuerst deutlich langsamer
  real testen. Jetzt alles vorbereiten; Nutzer startet URs erst auf Bereitschaft.
  Aktuell ausschließlich lesende Hardwareabfragen/Offline-/Mockvorbereitung;
  keine Power-/Brake-/Play-, Fahr-, Greifer- oder Controllerschaltbefehle.
- RechtsRF192.168.8.103/RR192.168.8.170, Domain66; Mock67, Simulation64.
- Gemessener Anfangsstatus beidePOWER_OFF/NORMAL, ros.urpSTOPPED, vorhandene
  Treiberlauscher, commands[], keine eigenen Treiberstarts. Statusdatei
  setup/logs/carton-hardware-preparation-status-20261116.json.
- Lücken vor Realgriff: Taskbackend bisherSimulation-only; kein bewährter
  Realgreiferadapter/Klemmkraftabgleich, Welt-/Tisch-/Basenextrinsiken nominal.
  Reine Timestamp-Gleichheit unabhängiger UR-Trajektorien reicht für tragenden
  starren Verbund nicht; gemeinsames Objektzeitgesetz und Ist-Relativfehler
  einschließlich UR-Speedscaling erforderlich. Kein Simplan direkt ausführen.
- Nutzerfrage zur bisherigen Realgreiferbedienung gestellt; lesbaren Zugang
  zuerst prüfen. Vorbereitung darf keine automatische Aktivierungsfahrt enthalten.
- Bereiche: neue getrennte Hardware-Vorbereitung/Read-only-Prüfwerkzeuge,
  eigenes langsames Profil, Dokumentation und zielgerichtete Tests. Bestehende
  laufende Dreh-/Vierarmarbeiten und Treiber erhalten; keine Dienstneustarts.

## Stand der Vorbereitung

- Nutzer: Greifer bislang nicht benutzt; ROS-Steuerung erkunden. Beide echten
  Robotiq-Server63352 GET-erreichbar, ACT0/STA0/FLT0; keineAktivierung.
- Neues Interfacepaket+ROS-Adapter, MONITOR ONLY alsDefault.23Tests und eigene
  ROS-Mockintegration67PASS; Read-Services beider echtenGreifer66PASS, Nodes
  danachExit0. Nur eigenes neues Interfacepaket gebaut, laufendePakete erhalten.
- Alle4nativeOutputstreams aufgenommen; aktuelle rechteTCPoffsets0.
  FactoryFK inURbase gegenüber nativenTCPs <1µm als interner Konsistenzcheck,
  keinerlei Weltregistrierungs-/externeGenauigkeitsfreigabe.
- Eigene Erststufenparameter0,5mm/s/5mmHub/.005rad/s/.005rad/s² dokumentiert,
  echterGreiferKraft-/Geschwindigkeitsabgleich offen. Profil nicht ausführbar.
- Software/Tests für Live-Vorprüfung fertig. VollständigerRealgriff bleibt
  offen: Greiferleerfahrt/realerGeometrieabgleich/gekoppelterHardwareObjektmaster
  mitgemeinsamerZeitbasis undGruppenstopps. NachNutzerstart zunächst nur frische
  Liveprüfung, kein automatischerHub. docs/carton_hardware_commissioning.md.

- Abschließender Readiness-Index: eigener Vorbereitungspfad/readiness-index.json
  bindet Code-/Profil-/Report-/Testdateien; Livebeobachtung vorbereitet,
  automatic_carton_lift_ready=false. EigeneROS-Testknoten beendet, keine
  Hardware-Aktivierung/-Fahrt; Nutzer kann als nächsten Schritt URs starten,
  danach zunächst frische lesende Prüfung.

## Vorbereitung während fremdem UR-Test,2026-11-17

- Nutzer meldet beideURsbereit, aber andererAgent nutzt Arme. Keine eigenen
  UR-/Greiferabfragen, Nodes, Controllerwechsel oder Schreibbefehle während
  dessen Zugriff; ausschließlich Offline-/eigeneMockarbeit. FremdeQuellen im
  Task-/Motionpaket werden nicht bearbeitet oder neugebaut.
- Karton lautNutzer wiederamPlatz. Nutzer erlaubt jederzeitigeOAK-Szenenprüfung;
  vorhandenenKameradienst/Lease nutzen, laufendenZugriff erhalten. NeuePose
  nach tatsächlicherÜbergabe messen, keinealtenHomeziele übernehmen.
- Arbeit: eigener reiner gemeinsamerObjekt-/Zeitbasiskern und Mockprüfungen,
  konkrete vorbereiteteÜbergabesequenz. VollständigerRealgriff bleibt offen;
  bloße Beendigung eines fremdenProzesses ist keine Bewegungsfreigabe.
