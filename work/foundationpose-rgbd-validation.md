# RGB-D-Geometrie an gespeicherten Boardbildern prüfen

- Status: **in Arbeit**, 2026-11-16 (Australia/Perth), Hauptagent.
- Nutzer erlaubt Fortsetzung und bietet Karton neben dem Roboter an. Zuerst
  gespeicherte8RGB-D-Paare prüfen; für diesen Schritt kein Karton nötig.
- Bereiche: eigene Offlineprüfung im OAK-Repo, Tests/Prüfbericht und Übergaben.
  Vorhandene Kalibrierungen/Assets/UR-/GPU-/Simdienste unverändert lassen.
- Festes Ausgabe-K/D=0, richtige40mm-Tischboards nach Markeridentität;
  Bildpunkte zur Pose und Prüfung trennen. Board-Tiefenebene mit RGB-Pose
  vergleichen, Tiefenlücken sichtbar halten. Keine absolute Genauigkeit oder
  globale Kalibrierung aus nur einer statischen Ansicht ableiten.
- Keine neue Kameraaufnahme oder Armbewegung vorgesehen. Weitere Benutzer-
  aktion nur bei tatsächlich unzureichendem Blick/Prüfaufbau anfordern.
