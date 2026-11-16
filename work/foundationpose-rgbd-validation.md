# RGB-D-Geometrie an gespeicherten Boardbildern prüfen

- Status: **in Arbeit – zusätzliche mobile Referenzaufnahmen**,
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
