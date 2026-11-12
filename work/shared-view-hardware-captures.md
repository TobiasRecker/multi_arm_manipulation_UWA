# Gemeinsame Sichtstellungen real anfahren und Wrist-HD aufnehmen

- Status: **in Arbeit**,2026-11-12,Hauptagent.
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
