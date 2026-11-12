# ROS-Steuerbereitschaft links vorne prüfen

- Status: **abgeschlossen – ROS-Steuerverbindung bereit, kein Bewegungstest**,2026-11-12, Hauptagent LF-ROS.
- Nutzerauftrag: prüfen, ob UR5 links vorne inzwischen per ROS steuerbar ist.
- Arm: left_front,192.168.8.2, Serial2017356443, Domain66. AndereArme erhalten.
- Zuerst lesend: nativeRobot-/Safety-/Programmzustände, frische JointStates,
  Hardwareinterfaces, Controller-/External-Control-Verbindung prüfen.
- Bestehender eigener Dienst uwa-left-front-hardware-driver seit früherem
  Fehlstart aktiv; bei bestätigtem unkonfiguriertem Hardwarezustand gezielter
  Neustart dieses Treibers vorgesehen. Keine automatischen Power/Brake/Play-
  Aufrufe, Schutzquittierung oder Fahrziele für diesen Diagnoseauftrag.
- Keine Änderungen an Roboter-/Feldbus-/Sicherheitskonfiguration. Kein pauschales
  Prozesskill, keine anderen Treiber-/OAK-/RViz-Dienste stoppen.
- Ergebnisse lokal setup/logs/left-front-ros-readiness-20261112 und HANDOVER.

- Ergebnis: nachNeustart erneut3×RTDE-IN_USE/speed_slider_mask,keineROS-Telemetrie.
  Output-onlyRTDE71Samples/7s funktioniert. Nutzer nachFeldbusstatusgefragt.
  DauerhafteDiagnose `setup/logs/left-front-ros-readiness-20261112/153340`; HANDOVER/Inventar/Bedienungaktualisiert.

- Nutzer bestätigt EtherNet/IP aktiviert. Manueller nächster Schritt:
  bei fehlender SPS-Nutzung deaktivieren und Installation speichern; danach
  gezielter ROS-Neustart/Steuerbereitschaftscheck. Deaktivierung noch unbestätigt.

- Nutzer meldet EtherNet/IP deaktiviert und Installation gespeichert. Jetzt
  erneutegezielteInitialisierung nur LF-Treiber, keinePlay-/Fahrziele.
  Parallele three-camera-board-capture-Arbeit und sämtlicheKameradienste erhalten.

- NeuerCheckPOSITIV:Hardwareactive,Broadcasteraktiv,vierMotioncontrollerinactive.
  2320Samples/20s,124,95Hz,max334,5msLücke. RTDEInputkonfliktbehoben.
- NativeProgrammnochSTOPPED. NutzerumStartvonros.urpgebeten,Host209/Port51002.
  BisBestätigungkeineweitereZustands-/Motionoperation;keinFahrzielgesendet.
  NeueNachweise `setup/logs/left-front-ros-readiness-20261112/ethernetip-off-155447`.

- Abschluss: Nutzerstart ros.urp bestätigt,PLAYING/NORMAL,ROSprogram_runningtrue.
  Reverse/Trajectory/CommandESTAB,Ready-to-receiveTreibermeldung.9Controller
  gelesen,5active/4Motioninactive. KeineFahrziele. HANDOVER/Bedienungaktualisiert.
