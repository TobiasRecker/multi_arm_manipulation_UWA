# Gemeinsame Kalibrieraufnahme als Library-Programm

Stand 23.11.2026. **Multi-camera calibration capture**
(`multi-camera-calibration-capture-v1`) speichert den gesamten Aufnahmeaufbau:
vier UR-Beobachtungsziele, ihre serielle Anfahrt und die native Sechskamera-GUI.

In **UWA Robot Power → Program library → Multi-camera calibration capture**:

- **Start capture setup** liest die aktuellen Gelenke und die Modellbindung
  vom N100. ROSmini plant und prüft die Wege zu den gespeicherten Zielen.
  Danach fahren links vorne, links hinten, rechts vorne und rechts hinten
  nacheinander. Bereits erreichte Ziele werden ausgelassen. Erst nach Erfolg
  öffnet sich **UWA Camera Capture**.
- **Open capture GUI** öffnet ausschließlich die Aufnahmeoberfläche. Ein
  laufendes Sechskamerafenster wird weiterverwendet. Diese Aktion fordert
  keine Roboterbewegung an und benötigt keine gültige OAK4-Tischreferenz.

Für die Anfahrt müssen alle Arme unbeladen und über **UWA Robot Power**
vorbereitet sein: RUNNING, NORMAL und External Control PLAYING. Den
Arbeitsraum vor Ort freigeben. Das Programm schaltet keine Antriebe ein und
setzt keine Schutzstopps zurück. Bei einer Sperre zuerst **Safety log** lesen.
Eine bestehende Aufnahmesitzung vor einer nötigen Neupositionierung beenden.

Das Programm übernimmt das für diese Kamera-Anfahrten genehmigte
Solltempo **0,09 rad/s**. Hardwareprofil und bestehende Überwachung bleiben
bei **0,1 rad/s**. Die bisherigen Vollmodell-, Start-, Bahn- und nativen
Ausführungsprüfungen bleiben erhalten. Historische Trajektorien werden
nicht wiederverwendet. Modell-, Quellcode- und Planprüfsummen binden jeden Lauf.

Die Posen richten die vier Wrists auf die Mitte zwischen den Tischen aus.
Das entworfene gemeinsame Volumen für das mobile A4-Board beträgt ungefähr
50 × 50 × 25 cm um x/y = 0 und z = 1,20–1,45 m. Das ist eine geometrische
Abschätzung; die GUI zeigt die tatsächlich erkannten Boardecken je Kamera.

Mehrere Ansichten mit dem mobilen Board aufnehmen. Pro Klick **CAPTURE ALL
SIX** das Board still halten; nach **FRAMES ACQUIRED** darf es umgesetzt
werden. Vier Wrists, Ethernet-OAK4 und USB-OAK am N100 bleiben während der
Sitzung nativ aufnahmebereit. **Release cameras** oder Fensterschließen gibt
die Kameras frei und stellt die regulären Wrist-Dienste wieder her.

**Unterschied zu OAK4 camera calibration:** Das bisherige Programm bestimmt
die OAK4-Pose zum rechten Tischboard und veröffentlicht sie für zwölf Stunden.
Dieses neue Programm sammelt gemeinsame Bilder, Optik- und Gelenkmetadaten.
Es löst und aktiviert noch keine gemeinsame Kalibrierung und verlängert keine
Referenzgültigkeit. Eine höhere Genauigkeit muss am späteren Fit nachgewiesen
werden. Bei festen Armen und bewegtem Board entstehen gemeinsame
Referenzaufnahmen; eine unabhängige Hand-Auge-Kalibrierung benötigt zusätzlich
verschiedene Armstellungen.

Definition: `config/multi_camera_calibration.json`; Ziele:
`config/view_designs/mobile_board_volume_20261123.yaml`. Library-Laufprotokolle
liegen unter `setup/tasks/uwa_program_library/<run>/`, die Bildsitzungen unter
`setup/calibration/six_camera_mobile/`. Der N100 erhält nur zwei laufbezogene
Hilfsskripte und die neu geprüften Pläne, keine neue Guard-Installation.
