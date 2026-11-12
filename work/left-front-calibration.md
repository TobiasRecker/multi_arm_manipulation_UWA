# Links vorne: Kamera und relative Basislage kalibrieren

- Status: **in Arbeit**,2026-11-12, Hauptagent LF-Kalibrierung.
- NeuerNutzerauftrag: Position/Kamera des jetzt ROS-erreichbaren UR5 kalibrieren.
  Arm left_front,192.168.8.2; keine bisherige Frontlinks-Intrinsics/Hand-Auge.
- Vorbereitung: echteKamerafunktion/Optik/Board prüfen, frischeGelenke/Werkskinematik
  undvollständigeMoveIt-Szene nutzen. KeineÜbernahmefremderK/D oderMontagen.
- Nutzergefragt,oblinkes40mm-A3-BoardseitLeftRear-Kalibrierungunverändertbefestigt;
  relativeLF/LR-Basislage erfordertgleichefesteReferenz. GlobaleTisch-/Weltanker
  sindnichtvermessenundbleibenvorläufig.
- Bereiche: neueeigeneMesssitzung setup/calibration/hardware_handeye/left_front_20261112/,
  ggf.LeftFront-HD-Service überbestehendenKamerapfad, eigeneWeg-/Prüfartefakte,
  Bericht/AGENTS/HANDOVER. KeinebestehendenKalibrierprofileüberschreiben.
- NochkeineFahrziele: erstSicht-/Kameraprüfung undkonkretegeprüfteWegvorschau.
  NativeSicherheit/Collision/STOP bleiben. AndereArme/Kamera-GUI erhalten.

- Nutzerbestätigt unveränderteBoardbefestigung. HTTP-VGAfunktioniert,AE-Diagnose
  brauchbar,OriginalzustandvorweiterenFahrtenwiederhergestellt.
- ErsterWeg53,0s/531Samples/reinercheckPASS;alle4Armefrisch/keineungeprüften
  Homewerte. RVizDomain68eigenerVorschaudienstgeöffnet. NochkeineFahrt.
- HD-Bootstrap aufCB3i686 ohnegcc nichtmöglich;scheitertvorModusänderung.
  ErsteFahrtkonkretzurFreigabevorbereitet;danachBoard/Fokus/Bildmodus auswählen
  undgetrennteFit-/Prüfaufnahmen planen,keinealtenParameterfälschlichübernehmen.

- Fortsetzung nach PC-Absturz: Roboternetz erreichbar, alle vier URs RUNNING/NORMAL,
  ros.urp jeweils STOPPED; alle flüchtigen Hardwaretreiber/Vorschau verloren.
  Treiber für frische Vierarm-Kollisionszustände neu starten, Motioncontroller
  inaktiv; kein Power/Brake/Play oder Fahrziel automatisch auslösen.

- Nach PC-Absturz und Neustart16:17: alle vier URs RUNNING/NORMAL, ros.urp STOPPED.
  Vier flüchtige ROS-Hardwaretreiber mit inaktiven Bewegungscontrollern neu gestartet.
  Nach längerem DDS-Einlesen echte Gelenkstellungen aller vier Arme verfügbar.
  Aktueller Plan `preparation/first_view_rechecked/plan.json`: 53.0s,
  532 Kollisionssamples, voller Check-only bestanden.
  Fingerprint `9ad63ff3dd6c4da5fc9cf8666ec77fa6457b8d399179b7da5e1002a4379ecff0`; alte Vor-Absturz-Pläne nicht ausführen.
  Eigene Vorschau auf Domain68 wieder geöffnet. Vor realer erster Fahrt fehlen
  erneutes External Control links vorne und konkrete Freigabe des gezeigten Wegs.
  Keine Fahr-/Power-/Brake-/Play-Befehle gesendet.

- Nutzer gibt den nach Absturz neu geprüften Einzelweg frei („ist alles frei“).
  Erstversuche vor Fahrziel abgewiesen (Controller fehlte; dann Action-Discovery).
  Vorhandene Parameter im passenden LF-Namensraum gesetzt, getrennte ROS-Load-/
  Configure-Dienste erfolgreich; keine Treiber-/UR-Neustarts. Action-Discovery
  vor Aktivierung mit längerem Zeitfenster, native Safety/Link/4arm-Guards erhalten.
- Freigegebener Einzelweg real PASS, Result0, Endfehler 0,0000623rad; keine
  anderen Armziele. Vier Diagnosebilder, drei aktuelle mit je24/24 Boardecken.
  Erster echter Fit-Datensatz sample_000:640×480,24Ecken,3 verschiedene Frames
  im Stillstand, eigener Fokus245Manual/60590µsManual/Gain19. Originalsettings
  und Nachweise in preparation/. Noch kein Fit/keine Basispose aktiviert.
