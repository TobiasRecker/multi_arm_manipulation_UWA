# Vier Armkameras plus OAK für Objektrekonstruktion

Stand12.11.2026. Nutzerziel: Objekt in einem gemeinsamen Tischbereich, vier
Wrist-Kameras darauf ausrichten und zusammen mitOAK fünfFotos pro Aufnahmeschritt
speichern. Optional wenigeZentimeter Kameraverschiebung für zusätzlicheAnsichten.
Dies ist eine **Auslegung und Literaturbewertung**, kein ausgeführter Fahrplan.

## Was der Ausbau bringen kann

Vier verschiedene Blickrichtungen können gegenüber dem bisherigen OAK/Front-
Messpaar mehr Außenflächen und Innenwände erfassen. Der gemeinsame sichtbare
Objektbereich ist erst zu prüfen: Die bisherigen Vierarm-Designposen betrachten
jeweils das eigene Tischboard. Sie beweisen keine gemeinsame Sicht aller Arme
auf einen Karton in der Mitte eines bestimmtenTischs. Für den ersten Entwurf
bietet sich der bisherige rechteBoardbereich an; das ist eine Designannahme.

Entscheidend sind überlappende Ansichten und freie Sicht. Ein höheres Bildzähler-
Ergebnis allein garantiert keine vollständigere oder genauereGeometrie. Die
Unterseite bleibt auf dem Tisch verdeckt; sie braucht beiBedarf einen getrennten
zweiten Aufbau. EinfarbigePappe bietet wenigBildtextur, reflektierendeKanten und
bewegteArme können Zuordnung erschweren. Objektmasken und gezielteBlickwinkel
gehören deshalb zur Pipeline.

Vorschlag: zuerst eine feste gemeinsame Stellung jeArm plusOAK, also5Ansichten.
Danach proWrist insgesamt3–5 verteilteStellungen:13–21verschiedenePerspektiven
mit der einen festenOAK. FünfAufnahmerunden können25Fotos erzeugen, aber die
fünfOAK-Fotos stammen weiterhin aus derselbenPerspektive. WiederholteBurstframes
sind ebenfalls keine neuen Kamerastellungen.

## Kleine Bewegungen bleiben zu planen

WenigeZentimeterTCP-Verschiebung sind kein Nachweis für Kollisionsfreiheit.
IK-Zweigwechsel, Drehungen vonEllbogen/Handgelenken, andereArme, Tisch, Objekt,
Greifer und Kameragehäuse müssen im vollständigenGelenkweg betrachtet werden.
Bestehende Kollisions- und nativeUR-Stoppfunktionen bleiben erhalten. Nicht
modellierte Kabel/Fixtures werden durch einen Planer nicht automatisch erfasst.

ZumEinordnen:2cm seitlicheVerschiebung bei50cmObjektabstand ändern die Richtung
zum Objekt um etwa2,29°,5cm um5,71° (`atan(baseline/distance)`). Das hilft lokaler
Parallaxe, erschließt aber kaum eine völligverdeckteRückseite. Für zusätzliche
Flächen sind unterschiedliche Azimute und Höhen zu bewerten. Der Abstand folgt
Objektgröße und tatsächlicherK/D-Projektion; der52cm-Karton passt nicht automatisch
bei jedem kleinenKameraabstand komplett ins Bild.

Zunächst Arme seriell in die gemeinsamenGrundstellungen bringen und bei weiteren
Ansichten jeweils einenArm bewegen. AlleArme vorFotos anhandTelemetrie still
bestätigen. Das vorhandene Kamera-only-Verfahren kann dieFotos gemeinsam anfordern,
bietet aber keineBelichtungssynchronität; Objekt/Referenz müssen währenddessen
ruhen. Kein pauschaler Neustart oder Eingriff in laufendeKalibrierreihen.

## Geeignete Verfahren aus der Literatur

### COLMAP und klassische Mehrbildrekonstruktion

COLMAP unterstützt Kameraparameter, bekanntePosen und Bündelausgleich. Das eignet
sich als geometrischeVergleichsbasis für unsere kalibriertenFotos. Für die
Oberfläche ist anschließend beispielsweiseOpenMVS ein passender Kandidat; dessen
Eingang sind Kameraposen und eine dünnePunktwolke, Ausgabe ein texturiertesMesh.
Primärquellen: [COLMAP](https://colmap.github.io/faq.html),
[OpenMVS](https://github.com/cdcseacave/openMVS).

Die vier unabhängig bewegtenArmkameras bilden **kein starresFünfkamerarig**.
COLMAPsRigmodell setzt feste relativeSensorposen voraus. Deshalb Kamera-Intrinsics
jephysischemSensor führen, Kameraposen jedoch jeAufnahme aktualisieren oder mit
geeignetenMessprioren optimieren. [Rig-Dokumentation](https://colmap.github.io/rigs.html).

### DUSt3R und MASt3R

DUSt3R schätzt Punktkarten und richtet mehrereAnsichten geometrisch aus.
MASt3R ergänzt dafür gelernte dichteMerkmale zur robusterenBildzuordnung, auch
bei stark unterschiedlichenAnsichten. Das ist ein sinnvollerForschungskandidat
für weniger manuellePunktzuordnung. Es ist noch nicht auf unserenKarton getestet.
Primärquellen: [DUSt3R](https://arxiv.org/abs/2312.14132),
[MASt3R](https://arxiv.org/abs/2406.09756),
[Implementierung](https://github.com/naver/mast3r).

### VGGT

VGGT schätzt aus Bildsammlungen unter anderemKameraparameter, Tiefen-/Punktkarten
und Bildpunktspuren. Das offizielleProjekt bietet einenCOLMAP-Export und optionalen
Bündelausgleich. Füruns käme es als zusätzlicheInitialisierung/Vergleichsrekonstruktion
in Betracht. EinegelernteTiefenschätzung ist weiterhin bildbasiert und keine echte
Tiefensensoraufnahme, aber auch kein Nachweis metrischerRichtigkeit. Maßstab und
Abweichungen mitBoards/ausgelassenenAnsichten kontrollieren.
[OffizielleImplementierung](https://github.com/facebookresearch/vggt).

### NeRF und Gaussian Splatting

Diese Verfahren sind für Ansichtsynthese und anschaulicheDarstellung interessant.
Ein solchesDarstellungsmodell ist noch kein editierbarer, maßhaltigerCAD-Solid.
Meshing ist möglich; Nerfstudio dokumentiert dafür unteranderemTSDF-/Poisson-
Exporte. FürunserZiel würde anschließend weiter eineGeometrie-/CAD-Anpassung
folgen. [Geometrieexport](https://docs.nerf.studio/quickstart/export_geometry.html).

## Empfehlung für unsere Pipeline

DieAufnahme bleibt unabhängig vomRekonstruktionsbackend:

`5-Kamera-Datensatz → Objektmasken → Geometrie/Punktwolke → Oberflächenmesh → einfacherCAD-Fit`

Dieausgewählten, passenden K/D undBildgrößen, Fokus, Kamerapose proFoto,
Referenzmaßstab, Telemetrie/Belichtungsfenster undQualitätskennzeichnung müssen
mitgespeichert werden. DieObjektmasken verhindern, dassArme/Hintergrund stattObjekt
rekonstruiert werden; Boardreferenzen dürfen für diePosenschätzung separat dienen.
EinTeil derAnsichten wird vorAuswertung ausschließlich zurKontrolle reserviert.

Zuerst den bisherigenKartontest mitmehrAnsichten und dem existierendenCAD-Fit
wiederholen. Parallel denselben eingefrorenenDatensatz mit klassischerGeometrie
und späterMASt3R oderVGGT auswerten. So lässtsich beobachten, ob mehrDetails und
wenigerHandarbeit entstehen und wie gut zusätzlicheAnsichten vorhergesagt werden.
Eine komplexereMeshoberfläche wird nicht automatisch zu bearbeitbarenCAD-Flächen;
für einfacheObjekte behalten wir dieParameter-/Ebenen-/Quaderanpassung.

## Lokaler Stand und nächste konkrete Umsetzung

- Alle vier Armkameras haben inzwischen einen nativenHD-Aufnahmepfad; links
  vorne wurde derCB3-Bootstrap in der parallelenAufgabe erfolgreich erweitert.
  Derbisherige CaptureRig-Code verwaltet jedoch nur zweiWristkameras plusOAK.
- HD-Kalibrierungen rechts hinten und links vorne laufen beziehungsweise werden
  gerade fortgesetzt. Nicht als bereits erfolgreich abgeschlossen oderaktiviert
  voraussetzen. ProKamera passendeK/D/Fokus und Pose-/Boardreferenz prüfen.
- DieserPC hat laut lokalem`lspci` IntelArrowLake-Grafik, kein erkanntesNVIDIA/CUDA-
  Gerät. COLMAP-Feature-/Sparse-Schritte können aufCPU laufen; dessen eigene
  dichteRekonstruktion benötigtCUDA. Für schwere gelernteBackends erst begrenzten
  Test oder geeignetenGPU-Rechner vorsehen, keine bestehendeROS-Umgebung ersetzen.
  [COLMAP ohneCUDA](https://colmap.github.io/faq.html#available-functionality-without-gpu-cuda).
- Designprofil: `config/digitization/five_camera_scan_design.yaml`. Es wird von
  keinemBewegungsprogramm eingelesen und ist ausdrücklich nicht ausführbar.
  Noch keine gemeinsamenVierarm-Zielposen/Verbindungswege berechnet odergeprüft;
  keine Kameraaufnahme, echteArmbewegung, Paketinstallation oderGPU-Modellausführung
  für dieseRecherche durchgeführt.

AlsNächstes braucht es einen Objekt-/Referenzbereich mit vollständiger gemeinsamer
Sicht, passendeKameraprofile, einenfrischenVierarmzustand und konkretevollständig
geprüfte Grund-/Zusatzposen. Erst daraus entsteht eine inRViz reviewbareFahrfolge.
