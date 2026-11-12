# OAK-Pose und sichtfreundliche UR-Stellungen

- Status: **abgeschlossen – grobe Pose und Vierarm-Entwurf geprüft**,2026-11-12,Hauptagent.
- Auftrag: grobe OAK-Pose aus echtem8K-Foto/Live-Optikdaten relativ rechtemTisch
  schätzen; UR-Konfigurationen für wenigVerdeckung/gemeinsamesWrist-OAK-Feld finden.
- Keine realeArmfahrt/Power/Brake/Play. Geprüfte Modellstellungen/Vorschläge und
  gegebenenfalls isolierteVorschau; keine bekannteTisch-/Boardvermessung erfinden.
- Bereiche: neue gezieltePose-/Sichtplanung, versionierte lokaleSchätzartefakte,
  Dokumentation/HANDOVER. GemeinsamesKalibrierprofil nicht still ändern; parallele
  Front-HD-Adoption erhält eigeneDateien/Standardlayoutzuständigkeit.
- OAK-Factory-K/D nur lesend,8K-Foto unverändert. Board→Optik gemessen ausBild;
  Tisch→Board-Platzierung weiterhin Annahme, keine endgültigeOAK-Kalibrierung.
- Sichtqualität: Pixel-/Boardabdeckung und nominaleArmverdeckung getrennt prüfen,
  Kollisionsfreiheit derZielstellungen; echteWege später frisch planen/freigeben.

- Ergebnis: rechterTisch→OAKoptisch[.806,.025,.958]m/33.54°nachunten; bei.90m
  Tischhöhe1.858m. ZweitesBoard bestätigtHöhe/Neigung,relativeBoardlageweicht6cm
  vomNominal ab. Kein globalesOAK-/Tisch-/Basenprofil daraus aktiviert.
- AktuellesProfilhardware_20261112_v2 respektiert. Kandidatenfüralle4Arme,
 24WristEcken/48OAKEcken, modelliertefreieTischfläche54→78%,A4-gemeinsame
  Sicht zusätzlichgeprüft. ExperimentellesDesign-YAML undlokaleArtefaktegespeichert.
- VollständigeSerien-Verbindungsprüfung3685Samples/367.9s, keineHardwarefahrt.
  LinksFrontistnominellesNutzerHome, daherHardwareausführungexplizitfalse.
- StatischeRViz-Domain70offen(28Joints/9Marker),5GeometrietestsPASS. Keine
  anderenDienste/Arm-/Kameraparametergeändert. Bericht/README/HANDOVERgepflegt.
