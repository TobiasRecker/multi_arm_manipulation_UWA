# Gemeinsame ROS-Greifersteuerung

- Status: abgeschlossen – ROS-Schnittstelle/Mockprüfung und reale Lesedienste,
  2026-11-17 (Australia/Perth), Hauptagent dieses Chats.
- Nutzerauftrag: wiederverwendbare ROS-Funktionen zum Öffnen, Schließen mit
  definierter Krafteinstellung und Anfahren einer Öffnung; für andere Agenten
  dokumentieren. Keine neue reale Finger-/Armbewegung in dieser Umsetzung.
- Umsetzung in eigenem Paket uwa_cell_gripper_control, vorhandenen geprüften
  Robotiq-Transport wiederverwenden. Alle vier Arme, Domain66 real/67Mock.
  Neue komfortable Action neben kompatiblem Rohregister-Endpunkt; Status/
  Fähigkeiten als Services, Python-/CLI-Client, gemeinsamer Start.
- Kraft/Weite bisher nicht physisch kalibriert. Nutzer bestätigt auf Rückfrage
  am17.11. ausdrücklich Rohkraft/relative Öffnung als ausreichenden ersten
  Umfang. Explizite Rohwerte und prozentualer Registerhub, keine unbewiesene
  N-/mm-Zuordnung; keine weitere Implementierung für diese Bestätigung nötig.
- Nachfolgende Präzisierung17.11.: Datenblatt-Sollwerte ohne eigene Kalibrierung
  genügen. Nominelle Python-/CLI-Helfer ergänzt:85mmEndpunktinterpolation,
  Kraft explizit lineare20–235N-Näherung, nicht gemessene/garantierteIstkraft.
  Quellen und Grenzen in docs/gripper_ros_api.md, Servercaps unverändert.
 25API-/Client-/CLI-TestsPASS; keine neue Hardwarebewegung, kein Node-/
  Dienstneustart für diese reine Clientumrechnung nötig.
- Betroffene Bereiche: neues eigenes Paket, Erweiterung des Interfacepakets,
  Doku/AGENTS/HANDOVER. Task-/Motion-/Kartonquellen und fremde Prozesse erhalten.
  Nur diese zwei Pakete bauen; eigene Mocktests und ggf.reinlesender Livetest.
- Vorhandene Geräte-Lease mit altem Adapter teilen; kein doppelter Writer,
  keine automatische Aktivierung, Öffnung oder Freigabe beim Start/Exit.
- Ergebnis: eigenes Paket gebaut; Komfort-Action `/operate`, kompatible rohe
  `/command`, `/read`, `/capabilities`, Statusfeedback. Python-/CLI-Helfer und
  Vierarm-Launch, eigener `uwa-grippers.service` jetzt MONITOR ONLY verfügbar.
-13reineAPI-Prüfungen PASS; ROS-Mock67 mit Loopback-Gerät bestätigt Öffnen,
  Aktivieren, relativeWeite, kontaktbeendetesSchließen/Rohkraft, Caps, alte/neue
  Action gegenseitig ausgeschlossen, Prozess-Lease und kein Write beiMonitor/
  Start/Exit. Alle4realen Read-/Capabilities-Services geprüft; commands_sent[].
- Doku docs/gripper_ros_api.md mit ROS-/Python-/CLI-Beispielen, AGENTS/HANDOVER/
  README ergänzt. Kein fremder Prozess oder Task-/Motionpaket verändert.
  Noch offen als eigener Messauftrag: Kraft inN, geometrischeWeite inmm und
  qualifizierterFingerstopp; keine Freigabe eines belasteten Kartongriffs.
- Erste realeClient-Discovery nach3s nochunvollständig; Graphprüfung zeigt
  alleServices. ReineVerfügbarkeitssuchevorAnfragenjetztbis10s, danachalle4
  Status-/Capabilities-AufrufePASS. KeinGeräte-/Kommandotimeoutverlängert.
  DienstistSitzungsdienstohneBootautostart, StartsendenkeineGerätekommandos.
