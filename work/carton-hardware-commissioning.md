# Langsamer Kartongriff in der echten Zelle

- Aktualisierung17.11.ausseparatemunbeladenemVierarmtest: alle4Greiferreal
  aktiviert/vollgeöffnet; SPE16/FOR0zurückgelesen. TransportjetztParameter
  einzelnvorPositionsänderungbestätigen. Alter16.11.-Readiness-Codehashdes
  Greifertransportsüberholt; keinbeladenerGriff/keineN-Kalibrierungqualifiziert.
  Bericht docs/hardware_commissioning_2026-11-17.md. VierArmeabschließend
  verriegelt/stationär, kein automatischerKartonhub ausdiesemNachweis.

- Status: **Übergabe/realer ROS-Greiferteilhub/Offline-Anfahrkandidat geprüft;
  automatischer Realgriff noch offen**,2026-11-17(Australia/Perth).
- Nutzerauftrag: bestehenden Zweiarm-Kartonablauf zuerst deutlich langsamer
  real testen. Jetzt alles vorbereiten; Nutzer startet URs erst auf Bereitschaft.
  Bis16.11.ausschließlichlesend; nachÜbergabe17.11.vierexpliziteROS-
  Greiferteilhubziele ausgeführt, sieheunten. KeinePower-/Brake-/Play-, Armfahr-
  oderControllerschaltbefehle.
- RechtsRF192.168.8.103/RR192.168.8.170, Domain66; Mock67, Simulation64.
- Gemessener Anfangsstatus beidePOWER_OFF/NORMAL, ros.urpSTOPPED, vorhandene
  Treiberlauscher, commands[], keine eigenen Treiberstarts. Statusdatei
  setup/logs/carton-hardware-preparation-status-20261116.json.
- Lücken vor Realgriff: Taskbackend bisherSimulation-only; Klemmkraft-/
  Öffnungsabgleich offen, Welt-/Tisch-/Basenextrinsiken vorläufig.
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

## Tatsächliche Übergabe und frische Szene,2026-11-17

- Nutzer bestätigt „Jetzt frei“. Beide rechtenURs RUNNING/NORMAL/Remote,
  ros.urpPLAYING/Reverseverbunden. ViernativeOutputstreamsstationärbeobachtet;
  rechteHoldsaktiv, Bewegungskontrollerinaktiv. KeineeigenenSchreibbefehle.
- Default-FastDDS-Client findet beideManager; erzwungenesUDPv4war inkompatibel
  zumheutigenTreibertransport. KeineTreiberänderung/keinNeustart.
- OAKStandard8K/Fokus116/10:31:25bestätigtKartonamPlatz, Kamerageschlossen.
  OfflinePose69Inlier/2,458px, vorläufigeWeltpose1,43degNeigung. Keinabsoluter
  Genauigkeits-/Greifnachweis. setup/tasks/carton_hardware_preparation_20261117_01/.
- Gemeinsamer transportfreierObjektreferenzkern14TestsPASS, festeOffsets/eine
  Uhr/nativeMinimalskalierung/Quellfrische/Relativfehler/Gruppenverriegelung.
  KeineechteIK-/Kommandotransport-/Stillstandsbestätigungsintegration. Taskpaket
  wegenparallelerSimkampagnenichtneugebaut. SoftwareprüfungkeinRealhub.
- Offline-Anfahrprüfung mitaktuellenFactorykinematiken, vollständigenFingerhüllen,
  aktuellem99,1cmLayout undKamera-Posekandidat: dritterFall findetgeprüften
  RF-dannRR-Weg in80mmVorposition. ZusätzlicheäquivalenteGelenkwindungen nahe
  Iststellung lösenSuchproblem; FK/volleSegmente erneutgeprüft. ZweiSuchfehl-
  versucheerhalten. KeineZeitplanung/Realtrajektorie; Modellnachweisallein.

## Echte ROS-Greiferteilfahrt nach Übergabe,2026-11-17

- GemeinsameROS-API inzwischenalsMonitor verfügbar. EinStartversucheines
  zweitenAdaptersanGeräteLeaseabgewiesen,0Goals. Harnessnutztjetztbestehende
  Read-/Capabilities-/Command-Endpunkte; reineLiveprüfungPASS.
- Nutzerauftrag langsamerRealtest: gemeinsamenDienst mitcapsFOR0/SPE16explizit
  enabled; RFundRRjeweils0→128→0,einzeln. Alle4ActionGoalsPASS, OBJ3/keinKontakt,
  Ziel128ist128undÖffnungsziel0istPOS3bestätigt. KeineAktivierung/Armbewegung.
- DanachDienstzurückMONITOR ONLY/caps0/16, beidenGreiferbleibenoffen.
  Alle4nativenArmstreamserneutstationär/letzteqd0. KeineArmcontrollerverändert.
- Artefakte setup/tasks/carton_gripper_ros_empty_stroke_20261117_01/ und
  carton_hardware_post_gripper_20261117_01/.24Referenz-/PregrasptestsPASS,
  ROS-MockmitseparaterFOR/SPE-BestätigungPASS. KeinN/mm-/Loadedstopnachweis.
- NächstertechnischerSchritt: realengekoppeltenObjekt-Kommandopfad integrieren
  undinMockprüfen, physischeAusrichtungvorKontakt; historisches.005rad/s-
  Profilnichtunteraktuellem.003rad/sWächterausführen. BestehendeGrenzen erhalten,
  KommandoboundmitgemessenenGeschwindigkeitspeaksabgleichen. NochkeinKartonhub.
