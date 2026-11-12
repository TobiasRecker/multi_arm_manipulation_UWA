# ROS-Steuerbereitschaft links vorne prüfen

- Status: **abgeschlossen – ROS-Check negativ, RTDE-Eingang belegt**,2026-11-12, Hauptagent LF-ROS.
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
