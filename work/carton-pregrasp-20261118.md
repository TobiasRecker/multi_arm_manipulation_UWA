# Reale Zweiarm-Vor-Greifpose,18.11.2026

- Status: aktiv, Hauptagent Kartontest. Nutzer bittet ausdrücklich Karton zu
  erkennen und beide rechten URs in Vor-Greifpose zu fahren. Kein Griff/Hub.
- Aktuelle Basisanbindungen hardware_20261118_base_fixed_v1 fest übernehmen;
  OAK-Fokus107/aktuellen neuen Posekandidat getrennt und explizit verwenden.
- Aktuelles geometrisches Schutzprofil behalten: Kommando/Monitor0,1rad/s,
  amax0,2; keine zusätzliche Temposenkung/alte Langsamprofile.
- Lesender Start: alle4RUNNING/NORMAL aberProgrammeSTOPPED; Guardstationär,
  keineaktuellenFaults, alle4Holds/Watchdoggelatcht. KeineFahrt bisher.
- NeuesOAKStandardfoto14:55:32/Fokus107 gespeichert, Kamera geschlossen.
- Bereiche: bestehende Offline-/Real-Pregrasptools, Task-lokalerneuerKamerabezug,
  Quellen-/Geschwindigkeitsbindung. GemeinsamenWächter/Gerätenutzung erhalten.
- NötigeDienstvorbereitung: eigenesbestehendes Schutzprofil ggf.mitaktuellem
  Basisprofilneu laden (genehmigteKartontest-ProfilwechselinklAll4STOP/PLAY);
  keineGrenzänderung, keineSafetyquittierung. GreiferserviceMONITOR ONLY.

## Aktueller Nachweis / Umsetzung

- Foto setup/oak4/photos/20261118-145532-standard-230a88f2/, natives8K/107.
  Gesamtbild-Texturregistrierung bei1600/2400/3200nichtbelastbar; agentvisuell
  gewählterSuchausschnitt [2700,2150,4900,3800] ergibtmitunverändertemEstimator
 25Inlier/2,729px, BildposeVALID. KeineQualitätsgrenzeverringert. Crop-Kkorrekt
  durchHauptpunktverschiebung, globale3D-PoseimOriginal-OAK-Frame.
- AktuellenFokus107-K/DFit und14-Satz-OAK-Pose explizittasklokalverwendet;
  globaleProfilenichtausgewechselt. FesteübernommeneBasisanbindungenbeiderArme
  überihreT_base_oakgenutzt. NominalerAnzeigeweltframeersetztkeinenBasisbezug.
  SupplementalmodellprüftkonservativbeideKartonrepräsentationenzusammen;
  diesbedeutetnichtzweiObjekteundkeineerneuteBasisuntersuchung.
- Pfad/EndstellungenfürbeideArmeundserielleAusführungvollmodellgeprüft,
  offeneFingerhüllen,keineKarton-Touchausnahmen.150mmübergeplantemKontakt,
  nurunbeladeneAnfahrt. NominalRF32,998s/RR103,890s, Kommando/Monitor0,1,
  amax0,2undgeometric_onlyunverändert. RRhatgrößereHandgelenkdrehungausIstpose.
- BestehenderSchutzdienstmitgleichemProfilneugeladen/aktuellemBasismodell,
  genehmigteAll4-STOP/PLAY-SequenzunterHolds, keineSafetyquittierung. Alle4
  ProgrammeREADY, Watchdognichtgetrippt. GemeinsameGreifer-APIMONITOR ONLY.
- ZweiVorprüfversucheohneFahrziel:01verlangteunnötigaktivierteGreifer,
  obwohlalleACT0/STA0/OBJ0/POS3/PRE0offen;02bauteArmhistoryvorblockierenden
  GreiferstatuscallsaufundverlorDriveralignment-Samples. Korrektur: inaktiv
  offenakzeptieren(keinAktivierungszyklus), ArmhistorynachGreiferchecksfrisch
  aufbauen; keineFrischegrenzeverändert. Originalfehlerberichteerhalten.
- RunnererlaubtKommando=Monitor statt künstlicherTemposenkung; Default0,1.
  NeuePerarm-KamerabindungmitFrame-/Quell-/FK-Konsistenzprüfung; keinealte
  Weltregistrierung/widersprechendeBasisframe-Wahl.24gezielteTestsPASS,
  zusätzlicherGate-LaufnachInaktivregelPASS. Quellen-/Bildoverlay imscene01/.
- AktuellerRealversuch03: RFfährt, unabhängig native0,09347rad/s/RUNNING/NORMAL
  bestätigt; andere3gehalten, keinerleiFingerbefehle. ErgebnisnochNICHTals
  vollständigmelden. setup/tasks/carton_pregrasp_20261118_real03/.
