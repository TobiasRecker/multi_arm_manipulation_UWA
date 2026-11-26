# Object scan und Asset Library

In **UWA Robot Power → Program library → Object scan** legst du eine
Aufnahmesitzung an. Die **Asset Library** steht unter den Programmen und ist
über die Kopfzeile erreichbar. Beide Ansichten verwenden denselben lokalen
Webserver. Falls der Katalog bereits offen war, lädt ein neuer Start von
Robot Power den aktualisierten Server.

## Holzbalken aufnehmen

1. Lege den Balken auf den Tisch und beschreibe seine Lage und ein eindeutiges
   Merkmal wie Astloch, Stirnseite oder Markierung. Wähle **Rectangular solid**
   und die gewünschte Zahl der Haltearme oder **Ask Gemini to discuss**.
   Gemessene Außenmaße lassen sich in Millimetern als X Länge, Y Breite,
   Z Höhe eintragen oder später ergänzen.
2. Halte Objekt und Arme für **Capture view** ruhig. Die erste OAK4-
   HQ-Übersicht verwendet 3×6 RGB-HQ-HDR und 4×4 Stereo-HDR auf dem
   gemeinsamen entzerrten 1280×960-Gitter. Ein Stereo-Block nutzt den
   IR-Punktprojektor. Auch bei bestehenden Scans mit älterer Tiefenübersicht
   erstellt die nächste OAK4-Aufnahme einmal diese HQ-Übersicht.
   Anschließend verwendet OAK4 für Detailansichten native 48-MP-HQ-HDR-
   Farbfotos. OAK Pro liefert native Farbfotos im unveränderten Sensorframe.
   Die Wrist-Optionen verwenden die vorhandenen Kamera-Snapshots in VGA.
   Kameras werden nacheinander ausgelöst und anschließend freigegeben.
3. **Analyze with Gemini** sendet verkleinerte Ansichten und die
   Objektbeschreibung über das konfigurierte Antigravity-Konto. Gemini
   markiert das Objekt und mögliche Griffstellen im Bild, stellt Rückfragen
   und schlägt eine Anfahrt und Ansichten vor. Die lokale OAK4-Auswertung
   schätzt eine OBB im Kameraframe, wenn Bildregion und Tiefendaten passen.
   **Approve scan sequence** speichert die Entscheidung für diese Revision
   der Aufnahmefolge.
4. Erfasse zusätzlich die Enden und die vom Tisch oder einem Griff
   verdeckten Flächen. Für den ersten Durchlauf den Balken manuell in eine
   stabile andere Lage bringen und bei jeder Ansicht die Orientierung oder
   den verdeckten Bereich im Aufnahmelabel festhalten. **Assess coverage with
   Gemini** bewertet die sechs Flächen am Belegbild und schlägt fehlende
   Ansichten und Umpositionierungen vor. Nach neuen Bildern erneut prüfen.
5. Für Fototexturen wähle in **Face textures** die Fläche und eine klare
   Aufnahme. Ordne die vier sichtbaren Ecken der in der Oberfläche
   angegebenen Flächenrichtung zu. Der Export prüft den Hash des Originals
   und entzerrt die Fläche perspektivisch. Flächen ohne Zuordnung behalten
   die einfarbige Darstellung.
6. **Save asset draft** veröffentlicht die aktuelle Abdeckung, Bildquellen
   und vorhandene Modellversion. Das Quaderrezept exportiert GLB und OBJ/MTL
   in Metern sowie STEP in Millimetern. Ohne Bedienermaße kann der Entwurf
   die ausdrücklich als vorläufig gekennzeichneten lokalen RGB-D-Abmessungen
   nutzen. Fehlt eine Geometriequelle oder ist die Form **Other or unknown**,
   entsteht ein Foto- und Abdeckungsentwurf. Dichte Rekonstruktion allgemeiner
   Formen gehört zum separat dokumentierten Digitalisierungsworkflow.
   [Digitalisierungsworkflow](digitization_workflow.md)

Die Standardsitzungen liegen unter
`setup/tasks/uwa_program_library/object-scans/`. Das Scanmanifest verbindet
Aufnahmesätze und Bildhashes mit Vorschlag, Bedienfreigabe und Texturzuordnungen.
Ein gespeicherter Asset-Entwurf bleibt abrufbar, während weitere Ansichten
entstehen. **Update asset draft** veröffentlicht eine neue Version.

## Reale Fahrplanung

Das Scanprogramm macht bildbezogene Griffideen und gewünschte
Präsentationsansichten sichtbar. Der Bewegungsschritt ist als ausstehend
gekennzeichnet. Für den Balken benötigt er eine aktuelle Zellpose, gemessene
Abmessungen und Lastdaten, die überprüfte Kontaktgeometrie der beteiligten
Greifer sowie die vollständige Offline-Prüfung mit mitgeführtem Werkstück.
Erst ein aus dieser Prüfung erzeugter Plan gehört mit der konkreten
Startlage in **Motion Review**. Die Ergebnisse des
[Holzrahmen-Demos](wood_frame_demo.md) zeigen die Starrgriff- und
Kollisionsprüfung im Modell. Die [Wrist-Aufnahmeplanung](object_scan.md)
liefert eine Grundlage für Kamerabewegungen um ein ruhendes Objekt.

Eine auf der Stirnfläche abgestützte Übergabe braucht zusätzlich einen
Nachweis für die Auflage und den Lastpfad in jedem Wechsel. Dazu gehört
insbesondere der Zustand nach Öffnen des unteren Greifers und vor Freigabe
des oberen. Die aktuelle Scanfolge nutzt die manuelle stabile Umpositionierung
und zeigt weitere Ansichten als Aufnahmevorschläge.
