# Front-HD übernehmen und HD an beiden hinteren URs testen

- Status: **abgeschlossen – Front-HD übernommen, beide native Bildpfade geprüft**,2026-11-12,Hauptagent Front-HD.
- Expliziter Nutzerauftrag nach Erläuterung der nicht bestandenen Qualität:
  Front-HD-Daten übernehmen,HD-Bilder an right_rear(.170) und left_rear(.169)
  auf gleichem nativen Kamerapfad testen. Keine Armbewegung.
- Übernahme mit sichtbarer Bedienerentscheidung und unverändertem quality=false,
  versioniertem Profil; ursprüngliche Ergebnisse und Qualitätsgrenzen erhalten.
- Parallel arbeitet global-calibration-oak-boards an hardware_20261112_v1.
  Diese Änderungen erhalten; Front-HD wird darauf als eigenes Nachfolgeprofil
  aufgebaut. Standardlayout vor Aktivierung erneut lesen; keine fremden Builds/
  Dienste stoppen. Keine Hardware-/Gazebo-Neustarts für diesen Auftrag.
- Bereiche: calibration_profileLoader/gezielteTests,neuesProfil,HD-Diensttestdaten,
  HANDOVER/Bedien-/Kalibrierbericht. SSH ausschließlich Kamerapfad; keine Passwörter
  in Dateien. Zugriff/Versionen zuerst lesen,Restore nach jedem Kameratest prüfen.

- Ergebnis: Standardprofilhardware_20261112_v2 installiert und Loader/URDF geprüft.
  Front-HD-K/D+X/Y übernommen mit originalpassed:false,proArtefaktSHA-gebundener
  Nutzerentscheidung; Rear-/Kinematikdatenv1 unverändert. Keine Welt-/Basenpose.
- 45gezielteTests PASS,3LyricalPaketebaut;Test-/Buildlogs uwa-front-hd-adoption-*.
- Linksrear echterHD-Service PASS,3Bilder2592×1944/je24Ecken,16,12s,RestoreNormal
  undalleOriginalsettingsidentisch. Servicebleibtbereit,keinArmbewegt.
- Rechtsrear native2592×1944-Bilder erhalten,aberUCC1.11.1+Autofokus-ROI-Restore
  scheitert: initialX1/Y1=165/134,amEnde158/102. VorherigeROI konnteHTTP-seitig
  nichtidentischhergestelltwerden. KameraNormal,Auto-Modi/LED/andereSettings
  erhalten. WeitereAufrufe indieserbekanntenKonstellation vorModewechselabgelehnt,
  echterGuardtest ohneZustandsänderungbestätigt. KeineweitereNativeSeriegestartet.
- LED-CodierungbeiLegacy1.11.1/3.44.0gemesseninkompatibel,nunreadbackgestützt
  behandelt. DynamischeAuto-AusgabewertevonKonfigurationunterschieden;
  manuellerFokus/Exposure/ROIbleibenexaktgeprüft. Passwortnichtgespeichert.
- NeueDoku docs/wrist_hd_other_arms_2026-11-12.md;README,AGENTS,HANDOVER,
  applied_calibrations,HD-Service-/Frontberichtgepflegt. KeinHardwaretreiber-/
  Gazebo-Neustart,keineArm-/Power-/Brake-/Programmaktion.
