# Vorläufige OAK-Registrierung übernommen

Auf ausdrücklichen Nutzerauftrag ist **hardware_20261112_v3** der gemeinsame
Standard für digitale Zelle, Gazebo, RViz und neue Modell-/Sichtplanungsaufrufe.
Das Profil ergänzt die [erste Drei-Kamera-Auswertung](three_camera_photo_evaluation_2026-11-12.md).
Die vorhandenen Roboterkinematiken, Intrinsics, Hand-Auge-Matrizen und benannten
Gelenkreferenzen ausv2 bleiben bytegleich. Keine echte Armfahrt, keine Änderung
an Hardwaretreibern, Sicherheitsparametern oder Kamerageräten.

Die Übernahme ist pro Ergebnis-SHA256 dokumentiert. Originaldateien behalten
`passed:false`, `diagnostic_only:true` und das damalige `calibration_applied:false`.
Das separate neue Profil kennzeichnet die aktuelle Anwendung als
`operator_accepted_preliminary`; es ersetzt keine automatische Qualitätsprüfung.

## Frame-Kette und Raumbezug

Die Fotoauswertung liefert `T_oak_optical_right_front_optical`. Für die Übernahme
wird die tatsächlich gemessene Front-Gelenkstellung vor der ersten Fitaufnahme
15:59:05 verwendet, mit individueller UR-Werkskinematik und der bereits ausdrücklich
übernommenen Front-HD-Hand-Auge-Matrix:

```
T_world_oak = T_world_front_base_at_registration
              @ FK_front_base_tool0(q_measured)
              @ T_tool0_front_optical
              @ inverse(T_oak_optical_front_optical)
```

Keine nominale Aufnahmepose und keine nachträglich angenommene Nullstellung.
Die Kette, Referenzwinkel, Quellen und Hashes liegen vollständig im Profil.
Die resultierende Kamera liegt ungefähr bei **[1,220;0,052;1,858]m** im aktuellen
Zell-Weltframe. Die Höhe passt zur2m-Stativgrenze.

**Der Welt-/Basisanker bleibt vorläufig.** Ein relativer Kamerafit vermisst keine
Tisch-/Roboterbasispose im Raum. Die gespeicherte Weltpose wird zum Zeitpunkt
der Registrierung eingefroren: Eine spätere Layoutänderung der Tische nimmt die
externe Stativkamera nicht mit. Bei neuer Basis-/Weltvermessung die Registrierung
gezielt neu ableiten, nicht unbemerkt den statischen Träger zum Tisch machen.

## Gemeinsame Verwendung

- `cell_layout_calibrated.yaml` lädt das versionierteProfilv3. Das nominale
  `cell_layout.yaml` bleibt als expliziter Design-/Rückfallmodus unverändert.
- Gazebo nutzt dieselbe optische Matrix, korrekt in seine+X-Sensorachse
  umgerechnet. OAK-Gehäuse, Stativ und Frustum werden dort bzw. in RViz an dieser
  Pose dargestellt; die approximierte Geometrie ist keine vermessene CAD-Hülle.
- TF in Simulationsdomain64: `world→oak_overview_rgb_optical_frame` und
  `world→real_oak4_rgb_optical_frame`. Zweiter Frame ist eine Registrierungs-
  Referenz, kein Nachweis eines aktiven echten Bildstreams. RViz-Marker tragen
  gut sichtbaren Text **PRELIMINARY / USER ACCEPTED – World anchor provisional**.
- `overview.sh` verwendet jetzt auch beim separaten Start das kalibrierte
  Standardlayout. Neuladen ersetzt ausschließlich die statische Kamera; Arme
  und Controller bleiben unverändert. Der Zelllaunch startet die Kamera erst
  nach erfolgreichem Einfügen des Zellmodells, um den beobachteten initialen
  Sensorverlust während des Szenenaufbaus zu vermeiden.
- Neue gemeinsame Foto-Sessions speichern `calibration_context.json` mit
  Profil-ID/Hash, vorläufiger Registrierung und den physischen OAK-Intrinsics.
  Bestehende Originalfotos/Manifeste bleiben unverändert.
- Hardware-/MoveIt-Modell- und Sichtplanungsaufrufe verwenden dasselbe Profil.
  Bereits gespeicherte Plan-Fingerprints ändern sich; alte Pläne regulär neu
  prüfen, keine Fingerprints umschreiben. Die OAK-/Stativgeometrie bleibt wie
  bisher **visual-only**, noch kein neu hinzugefügtes MoveIt-Kollisionshindernis.
- Der eigenständige OAK-HQ-Tiefen-Snapshot in Domain65 bleibt kamera-lokal.
  Seine rektifizierte Mono-Stereo-Projektion ist nicht der RGB-Optikframe; für
  eine spätere Weltwolke ist zusätzlich die passende interne Extrinsik nötig.

## Reale Optik und Renderergrenze

Reale RGB-Auswertung: vollständige OAK-Werks-K/D bei Fokus116, native8000×6000,
14Verzeichnungskoeffizienten. Exportiert als `oak4_camera_info.yaml` mit
`rational_polynomial`, alle Originalparameter erhalten.

Simulation:4000×3000/3fps, Brennweiten und Hauptpunkt passend skaliert. Das hier
installierte Jetty/Ogre2 meldet **ImageBrownDistortionModel is not supported**.
Darum erzeugt die OAK-Simulation ein **Pinhole-Bild** und meldet entsprechend
Nullverzeichnung. Keine nicht gerenderten Verzeichnungskoeffizienten als gültige
Bildgeometrie ausgeben. Die volle physische Rational14-Matrix wird nicht einfach
auf die ersten fünf Koeffizienten gekürzt.

Eine separat berechnete Brown5-Näherung bleibt für spätere kompatible Renderer
archiviert (`oak_simulation_optics.json`), wird hier aber nicht gerendert. Ihr
Fehler zur Rational14-Form auf einem unabhängigen80×60-Prüfgitter liegt bei
maximal rund6,32px im8K-Bild, entsprechend3,16px bei4K. Die Poseübernahme ist
von dieser Renderergrenze unabhängig. Hintere Wrist-HD-Intrinsics bei388
fehlen weiterhin; keine fremde oder hochskalierte VGA-Kalibrierung übernommen.

## Nachweise und Rückfall

Profil: `uwa_cell_description/config/calibration/hardware_20261112_v3/`.
Exportierwerkzeug: `python3 -m uwa_cell_control.export_oak_profile`, Eingaben,
Nutzerentscheidung und Zielprofil müssen ausdrücklich angegeben werden.
Früherev1/v2-Bündel und die Rohdaten bleiben erhalten.

40gezielte Offlineprüfungen bestanden: Matrixkonvention/FK, identische
Gazebo-/TF-Optik, feste Stativpose bei Tischverschiebung, erhaltene Gelenk-
Startstellungen und alte Roboterdateien, SHA-/Akzeptanzfehler, MoveIt/Overlay-
Consumer sowie Aufnahme-/Auswertungsregressionen. Drei Lyrical-Pakete gebaut.
Logs: `setup/logs/uwa-oak-profile-adoption-{build-final,tests-final}.log`.

Reale Simulatorprüfung und simuliertes Kamerabild unter
`setup/calibration/three_camera_evaluation_20261112/adoption-live/`:
Bildempfang, K/D, beide TFs, Gazebo-Sensorlinkpose und RViz-Abonnement geprüft;
alle neun Simulationscontroller aktiv, Simulationszeit läuft und Gelenke endlich.
Eine erste Prüfung ohne Bilder deckte den initialen Sensorverlust auf; gezieltes
Kamera-Neuladen behob ihn ohne Zell-/Roboter-Reset. Historische Fehlerlogs bleiben
erhalten. Die finale Prüfung verwendet das tatsächlich gerenderte Pinhole-Modell.

Rückfall: in einer eigenen Layout-Referenz `calibration_profile` aufv2 setzen
oder explizit das nominale Layout laden. Bereits laufende Modelle brauchen
gezieltes Neuladen; keine Hardwarefahrt ist Teil der Profilaktivierung.
