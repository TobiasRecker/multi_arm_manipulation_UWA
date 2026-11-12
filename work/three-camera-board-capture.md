# Drei-Kamera-Boardaufnahme

- Status: **abgeschlossen**,2026-11-12,Hauptagent.
- Nutzerauftrag: rechteArmebereitschaftlesen,frischeFotosRF/RR/OAK prüfen,
  kleineGUI mitaktuellerBoard-Sichtbarkeit undgemeinsamemAufnahmebutton bauen.
- Nutzerbestätigt mobilesA4-Board,DICT_4X4_100 IDs75–91,38mmFelder.
- Keine Armfahrt/Power/Brake/Play. Bestehende Kamera-Dienste/SSH-Keys verwenden;
  OAK-Vorschau koordiniert exklusiv freigeben vor HQ-Fotos,keinefremdenDienste stoppen.
- Bereiche: neueCapture-/Detektions-/QtModule,gezielteKamera-Restorekorrektur
  fallsnötig,Launcher/Tests/README/HANDOVER. Rohfotos untersetup/calibration/.
- GUI englisch,starkeText-/Kontrast-Rückmeldung. Live/Snapshot/Alter trennen;
  keinHardware-Syncbehaupten,BoardwährendgemeinsamerAufnahmestillhalten.
- Umgesetzt: board_capture.py/board_capture_gui.py, Launcher+Startmenü,
  zentralerFokus435/388/116, NativeWrist-LegacyRestore mitvollemReadback,
  OAKphoto --focus undlockkoordinierteSDK-Vorschau. KeineRoboterdienstneustarts.
- RealeDreierfotos: OAK24/RR24/RF8Ecken. Frontboardangeschnitten,Datenset
  ausdrücklichunvollständig. Foto-/GUIbericht docs/three_camera_capture.md.
- BuildPASS,30TestsPASS; echterGUIKlick/NativeDreierset/Live-Rückkehr/
  Pause-Dateisperre/Originalfokus-RestorePASS in gui_check/20261112_154921_20ecc2ad/.
- LesendeGelenkprobenvor/nachFotosets ergänzt,LiveProbePASS; vollständige
  Hinweise/Prüfpfade inHANDOVER. AndereLF-Aufgabe/Änderungenerhalten.
