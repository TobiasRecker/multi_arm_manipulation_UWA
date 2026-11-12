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
