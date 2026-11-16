# RGB-D-Geometrie an gespeicherten Boardbildern prüfen

- Status: **abgeschlossen – mobiler Vergleich, Genauigkeitsursache weiterhin offen**,
  2026-11-16 (Australia/Perth), Hauptagent.
- Nutzer erlaubt Fortsetzung und bietet Karton neben dem Roboter an. Zuerst
  gespeicherte8RGB-D-Paare prüfen; für diesen Schritt kein Karton nötig.
- Bereiche: eigene Offlineprüfung im OAK-Repo, Tests/Prüfbericht und Übergaben.
  Vorhandene Kalibrierungen/Assets/UR-/GPU-/Simdienste unverändert lassen.
- Festes Ausgabe-K/D=0, richtige40mm-Tischboards nach Markeridentität;
  Bildpunkte zur Pose und Prüfung trennen. Board-Tiefenebene mit RGB-Pose
  vergleichen, Tiefenlücken sichtbar halten. Keine absolute Genauigkeit oder
  globale Kalibrierung aus nur einer statischen Ansicht ableiten.
- Neue mobile Kameraaufnahmen jetzt nach Nutzerbestätigung des38mm-Bretts
  und Bereitschaft je Position beauftragt. Keine Armbewegung oder Geräte-
  kalibrierung; Kamerasperre und bestehende RGB-D-Profile erhalten.
- Ergebnis8Bilder:24Ecken,16Fit/8Prüfung, max0,3222px; SDK-Tiefe gegenüber
  RGB-Boardebene median+11,05mm. Keine unabhängige Genauigkeit/Offsetkorrektur.
- Nutzer misst5Felder200mm mit Lineal (unkalibrierte Unsicherheit). Mobiles
 38mm-A4-Board für zusätzliche ruhende Entfernungen/Neigungen angefragt.
- Neues Offlinewerkzeug,36Tests/9Subtests PASS und Bildprüfung. Bericht/
  Quellenhashes/Benutzermaß im bisherigen Datensatz unter board-check-v1/.
- Übergaben/Anleitung gepflegt, keine Dienste/Parameter oder Weltanker geändert.
- Nutzer bestätigt mobiles Brett vorhanden; Position1 bereit. Aufnahme
  beginnt über vorhandenen RGB-D-Pfad, Auswertung mit eigener38mm-Definition.
- Fünf Aufträge gespeichert:105733-aa93f0ad zu wenig mobileEcken;
 105958-67777ded auswertbar;110321-e55dece0 abgeschnitten;
 110510-b9ede6fe auswertbar;110823-dd33bfc2 auswertbar. Alle je8Paare.
- Kamera-Z ausRGB0,922/1,152/1,330m; maxPrüf-RMS0,452px. Mobile191mm/5Felder
  vom Nutzer mit Lineal gemessen, Nominal190mm unverändert. Hypothetisch
  isotropes Skalenszenario ergibt weiterhin unterschiedliche Z-Reste, keine
  Pauschalkorrektur belegt. Vergleich unter setup/oak4/rgbd/validation_20261116/.
-38Tests/9Subtests PASS; Kamera-Lease frei, keine Profilaktivierung. Anschließend
  erster realer Kartonversuch separat in work/foundationpose-carton-real.md.
