# Statische 6D-Posenbestimmung und dynamisches Objekttracking

- Status: **abgeschlossen – CPU-Prototyp live geprüft; Bewegungs-/Genauigkeitsabnahme offen**,
  2026-11-13.
- Nutzerziel: bekannte digitalisierte Assets wiederfinden; statisch vor
  Greifen/Manipulation möglichst genaue Pose, dynamisch schnelle Onlinepose.
- Zuerst gespeicherte Bilder/Asset verwenden; keine Armfahrt, keine Wiederaufnahme
  der pausierten Planungsvergleiche, keine ungefragten Kamera-/Dienstwechsel.
- Hardware: lokal Intel-Arrow-Lake-Grafik, keine erkannte NVIDIA-GPU. Nutzer
  bestätigt: zunächst Mini-PC, NVIDIA-Rechner möglicherweise später verfügbar;
  Beschaffung von Compute parallel durch ihn. Backendtausch offen halten.
- Gemeinsame Objekt-ID und unveränderter Assetframe; keine bekannte simulierte
  Objektpose als Schätz-Start oder Ergebnis unterschieben. Erst Kamerapose des
  Objekts; Weltpose nur mit zeitlich passender, gekennzeichneter Registrierung.
- Datenqualität/Verdeckung/Mehrdeutigkeit, Bildalter und LOST explizit ausgeben.
  Modellfehler und vorläufige Kamerakalibrierung begrenzen reale Genauigkeit.
- Geplante erste Bereiche: eigenständiger Trackingkern, assetgebundene
  Oberflächenmerkmale, offline statische Initialisierung und schnelle zeitliche
  Verfolgung mit Wiedererkennung; getrennte statische/dynamische Prüfung.
- Neues Paket uwa_cell_tracking gebaut: Textur-SIFT/3D-PnP-Initialisierung,
  statischer3-Frame-Burst, LK/PnP-Tracking, ROS-Pose/Status/Overlay mit Worker,
  explizites Start/Stop/Localize und Zeit-/Frische-/Kalibrierprüfungen.
- Offline6Tests und isolierter ROS-Replay Domain71 bestanden. Statische OAK-
  Auswertung1,4s; dynamische Kerne10msWrist/46msOAK, keine behauptetenLiveFPS.
  LF nicht verwendet; LR/RF bleiben teilsLOST/AMBIGUOUS, nichtzwangslokalisiert.
- ErgänzterProvider: opt-in OAK-Stream Domain65, bestehender SDK-Worker liefert
  zusätzliche Tracking-Metadaten/K/D und parametrisierte10fps/1600×1200;
  bestehende2fps/2000×1500-Vorschau unverändert. Gemeinsame Foto-Lease erhalten,
  keine fremden Kameranutzer stoppen oder Kamera automatisch resetten.
- Liveprüfung abgeschlossen:188Frames bei10,012empfangenenFPS,1600×1200/Fokus116.
  StatischePoseVALID bei0,42pxRMS und1,39sErgebnisalter;116OnlineVALID-Ausgaben
  inca12s, medianeKernzeit7,53ms, maxSDK-Bildalter128ms. TatsächlicheStream-K/D
  separat mit24Boardecken/0,256pxRMS geprüft; keineBoardpose alsTrackerprior.
- Kamera geschlossen undFoto-Leasefrei bestätigt. KeinArm-/Programm-/Dienst-
  Neustart, keine Wiederaufnahme der anderweitig pausierten Planungsarbeit.
- Abschließend6Offlineprüfungen und ROS-Replay71 nach Watchdogkorrektur PASS.
  Skript object_tracking.sh bietet oak/localize/track/stop/view; Rohdaten und
  Bank unter setup/tracking/, sichtbareVorschau output/images/carton_cpu_tracking.png.
- Offen: realeObjektbewegung/Verdeckung/Wiederfinden, unabhängigeKontrollmaße,
  robuste weitereAnsichten/Objekte und spätereGPU-/M3T-/Tiefenbackends. Kein
  manipulationsfreigegebenes oder weltweitvermessenen Ergebnis behauptet.
- DauerhafterStand/Bedienung docs/object_tracking.md, README/AGENTS/HANDOVER
  beiderbetroffenenRepos gepflegt; keine notwendigen weiteren Implementierungs-
  oder Prüfschritte für diesen ersten explizit abgegrenzten CPU-Prototyp.
