# Gemeinsame Sichtstellungen real anfahren und Wrist-HD aufnehmen

- Status: **abgeschlossen – drei Arme am Ziel, native HD-Bilder gesichert, SSH-Keys geprüft**,2026-11-12,Hauptagent.
- Nutzerauftrag: gezeigteSichtstellungen sequentiell real anfahren, danachWrist-HD.
  KonkreteZiele aus oak_pose_20261112/design_wrist/proposal.json freigegeben;
  frische vollständigeMoveIt-Wege undnativeSafety/ExternalControl erforderlich.
- LinksFront nochIPnull; Nutzer nachIP bzw.BestätigungHome/3Arme gefragt.
  Andere3Arme vorbereiten/Planung parallel; keine angenommeneLF-Fahrt.
- Bereiche: eigeneAusführungs-/Bildartefakte untersetup/calibration/shared_views_20261112,
  HANDOVER/Ergebnisbericht. Profile/Nominalgeometrie undfremdeProzesse erhalten.
- NativeHD jephysischerKamera; Front/LinksRearDienst vorhanden. RechtsRearUCC1.11.1
  mitAutoFocus blockiertwegenbekanntemROIRestorefehler; ggf.kameraeigenermanueller
  Fokus404 undvollständigerReadback/Restore prüfen,keineFirmwareänderung.
- KeineStoppquittierung oderautomatischeRückfahrt;beiFehler eigeneAction canceln/
  Controllerdeaktivieren,gesicherteBilderbehalten. Nur jeweils einenArm bewegen.

- Nutzerpräzisierung „8.2“ als192.168.8.2 verifiziert: LinksFrontUR5/Serial
 2017356443/PolyScope3.15.1,POWER_OFF/NORMAL/keinProgramm. NativeRemote-Abfrage
  istaufCB3nichtverfügbar; nichtalsLocal-Sperrebehandeln. Inventar ergänzt,
  Werkskinematikreinlesendextrahieren, KameraHTTPlesbarerreichbar.

- LinksFrontextrahierteWerkskinematik gespeichert/inventarreferenziert,Treiber
  eigenerDienstuwa-left-front-hardware-driver,keineMotioncontrolleraktivierung.
  Power-on erreichtIDLE,output-onlyRTDE liefert echteWinkel,keineHome-Annahme:
  [1.825827,-2.112189,1.579611,-1.060791,-1.504063,.896537]rad.
  RTDEInput-Initialisierung blockiert(speed_slider_mask schonbelegt),Nutzer
  umFeldbus-/Clientprüfungundfehlendesros.urp/ExternalControl51002gebeten.

- VierneuevorläufigeWege723/413/927/1386Samples/344.3sPASS; nochkeineFahrt.
  RRros.urp überMATCHgestartet. RunnerfürLive-Vollcheck/sequentielleFahrt/HD
  vorbereitet(lokalerSetup-Pfad),nativeSafety/LinkundVollszeneprüfen.
- Wartepunkte:LFExternalControl51002+RTDEInputfreigeben;vordereKamera-SSH-
  Anmeldungeninteraktiv. KeinePasswörterandenAgenten,keineHardwareresets.

- NutzerstelltLinksFrontvorerstzurück;keineFahrzieledorthin,dieanderen3weiter.
  NutzerbeauftragtSSH-SchlüsselstattwiederholterPassworteingabe. Eigenenprivaten
  Ed25519-SchlüsselaußerhalbGitangelegt,RF/LR/RRpublickeyinstalliertundfrische
  BatchMode-Key-Loginsverifiziert. LFerstabgewiesen,NutzernenntnunStandardzugang.
  KeinPasswortinDateien/Logs;KeynurPC209,keineWeiterleitungen/PTY.
- AktuellerLFReadbacknachparallelerNutzerarbeit:Version3.15.8,POWER_OFF,6Nullen.
  DieseAusgabenichtalsgemessenePoseverwenden. Read-onlyStreamfiltertPoweroff;
  nativeMessbereitschaftfürtatsächlicheWinkelnochherstellen. KeinUR-Stoppumgangen.

- Keyzugriff jetztalle4Hostsfunktionierend:RF/LR/RREd25519,LFwegennachgewiesenem
  OpenSSH6.0 eigenerRSA3072mitnurhostbezogenerLegacySignatur. FrischeLoginsPASS,
  unsupported eigeneED-ZeileLFentfernt,fremdeKeysbehalten. Backend reconnect
  automatisch;dauerhafteHostkeys;12Kamera/SSH-RegressionstestsPASS.
- NutzerstelltLFzurück;eswerdennurLR→RR→RFgefahren. LFbleibtungefahren,
  fortlaufenderOutput-onlyRTDE-Stream liefertwirklicheQ,keineNullannahme.
- LRZielerreicht2,07e-5radFehler. KurzeLF-DatenlückeinderRR-Fahrt führtezu
  Cancel+Controllerinaktiv,keineNativeStopquittierung. Danach25s/258Frames
  stabil,max.101sLücke;ReaderbeendetnichtmehrbeieinemReconnect-/Nichtdatenpaket,
  vorhandener.5s-FrischeGuardunverändert. UrsacheErstlückenichtabschließendbewiesen.
- AusaktuellerPoseRestwegeneugeprüft,LRohneerneutesZielübersprungen. RRZiel
  erreicht4,12e-5rad,RFfährtzurZielpose;danachdreiHD-Aufnahmen. LF-Kamera
  aktuellReconnectingCamera/UnbekannteHardware,keinHD-Versuchdort.

- Abschluss:alle3gefahrenenArmeamZiel/SafetyNORMAL/alleMotioncontrollerinaktiv.
  LR/RFje24EckenmitPASS-Restore;RRnative24EckenalsDiagnosebild,KameraOriginal-
  konfigurationnachgemessenerLegacyY-/LED-Korrekturtatsächlichwiederhergestellt.
  WorkerFehlberichtebleibenfalse,keineKalibrierbeobachtungvortäuschen.
- OAK-HQ-Gegensicht bestätigtalle3Boardsje17Marker/24Ecken. AlleBilderlokal,
  zusammengefassterBericht docs/shared_view_hardware_2026-11-12.md undErgebnis-
  summary/manifestgespeichert. KeineweiterenFahrziele,keinRückweg.
