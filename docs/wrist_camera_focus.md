# Reale Wrist Camera: Fokusfenster und Fotos

Stand2026-11-10. Für **right_rear** aus`config/hardware_inventory.yaml`.
Eigenes Qt-Fenster, unabhängig von ROS-Controllern/Robotermotion. Keine
SSH-Anmeldung erforderlich. Verwendet die intern in UCC1.11.3 nachgewiesene
HTTP-Schnittstelle, deren Schreibfunktion jetzt am eigenen Gerät geprüft ist.

## Öffnen

```bash
cd ~/UWA_ws
source src/multi_arm_manipulation_UWA/scripts/control_env.bash
ros2 run uwa_cell_control wrist_camera_gui
```

Das Sourcen stellt nur die Laufzeit bereit; das Fenster verwendet selbst
keine ROS-Verbindung. Es startet keine Robotertreiber und sendet keine
Bewegungs-, Power-/Brake-/Programm- oder Adminbefehle. IP ausschließlich aus
dem Inventar, standardmäßig192.168.8.170. Keine bestehenden GUIs/Dienste schließen.
Pro Kamera lässt sich nur ein solches Fokusfenster öffnen.

## Bedienen

- Vorschau: HTTP-JPEG ungefähr2Abfragen/s, tatsächlich640×480Pixel. Anzeige
  nennt Empfangszeit und wie lange die Bildbytes unverändert blieben. Dies ist
  kein garantierter Sensorbelichtungszeitstempel oder synchronisierter Stream.
- **Apply manual focus:** Regler oder Zahlenfeld0…1023 einstellen, dann klicken.
  Der Originalclient invertiert den Wert: API-Fokus=`1023−Reglerwert`. Dies sind
  keine Meter. Der Istwert steht separat über dem Regler. Auto wird ausgeschaltet;
  Antwort und Fokuswert werden zurückgelesen. Sichtbare Bildwirkung kann verzögert
  nach dem Readback eintreten; im Test etwa1–2s.
- **Run autofocus:** Auto aktivieren, gezielt nur Fokus triggern, Abschluss
  abfragen. Belichtung/Weißabgleich werden nicht mitgetriggert. Ergebnis im Bild
  prüfen; diese Funktion fokussiert den konfigurierten Kamerabereich und ist noch
  keine eigene ChArUco-ROI-Schärfeoptimierung.
- **Save photo + settings:** JPEG erneut abrufen und zusammen mit JSON zu
  Einstellungen, Hash und PC-Empfangszeit speichern. Keine Annotationen ins Bild
  einbrennen. Ein erfolgreicher Abruf beweist keine neue Belichtung.
- **Restore original focus:** Fokus/Auto-Modus vom Öffnen des Fensters
  wiederherstellen, aktuelle andere Einstellungen erhalten. Bei ursprünglichem
  Auto-Modus zusätzlich Autofokus triggern; dessen neuer numerischer Fokuswert
  darf vom ursprünglichen automatischen Wert abweichen.
- **Restore original focus when closing** ist standardmäßig aktiv. Nach eigenen
  Fokusänderungen wird beim normalen Schließen wiederhergestellt. Für bewusstes
  Beibehalten vorher abwählen. Öffnen/Schließen ohne eigene Fokusänderung sendet
  keine Einstellungsänderung. Bei fehlgeschlagener Wiederherstellung bleibt das
  Fenster offen und zeigt den Fehler. Ein harter Prozessabbruch kann keine
  Wiederherstellung garantieren; Originalwerte sind lokal gesichert.

Netzwerkaufrufe laufen in einem eigenen Thread. Sichtbare RUNNING-/FAILED- und
Abschlussmeldungen mit hohem Kontrast; während einer Aktion keine weiteren
Bedienkommandos. Es werden keine Meterkennlinie oder höheren Auflösungen vorgetäuscht.

Standard-Sitzungsordner:`$UWA_WS/setup/calibration/wrist_focus/<Zeit>/`.
`original_settings.json` wird beim Verbinden geschrieben. Alternativer Ordner:
`ros2 run uwa_cell_control wrist_camera_gui --output /absoluter/ordner`.
Bild-/Sitzungsdateien bleiben außerhalb des Repositorys.

## Nachweis am echten Gerät

- HTTP-POST manueller API-Fokus512 (Regler511) erfolgreich, Readback512/Manual;
  deutlich veränderte Bildschärfe. Dies war ein Testwert, **kein optimierter Fokus**.
- Ursprünglicher Auto-Modus wiederhergestellt und fokussiert. Der Autofokus
  bestimmte API-Wert408 (Regler615) für die damalige Szene. Dies ist keine
  allgemeine Empfehlung für andere Entfernungen/Boards.
- Ein zunächst zu strenger Vergleich verlangte auch im Auto-Modus denselben
  numerischen Stellwert; dieser Prüfmaßstab war falsch. Der Autofokus ermittelt
  seinen Wert neu. Manuelle Wiederherstellung bleibt numerisch geprüft, Auto-
  Wiederherstellung prüft Modus/Triggerabschluss und erhält alle anderen Felder.
- Späteres Kontrollfoto nach Auto-Wiederherstellung zeigt wieder deutliche
  Kanten, Laplace-Varianz485,65 gegenüber ca90 bei manuellem512. Diese Metrik
  beschreibt nur die damalige Szene, keine kalibrierte Qualitätsgrenze.
- Echte Qt-Knöpfe geprüft: Bildempfang, manueller Fokus, JPEG+JSON-Speicherung,
  Restore. Alle Nicht-Fokus-Einstellungen unverändert. Geprüftes Fenster bleibt
  für den Nutzer offen. Nachweis`setup/logs/uwa-wrist-focus-window/report.json`,
  Screenshots`manual-focus.png`/`ready.png`, Foto unter`photos/`.
- Vier HTTP-Adaptertests gegen lokalen Server bestanden: Mapping/Readback,
  Erhalt anderer Einstellungen bei Restore, Serverablehnung/Eingabegrenzen,
  Fotos mit korrekter Zeitstempelkennzeichnung sowie Fokus-only-Autotrigger.
  Log`setup/logs/uwa-wrist-focus-tests.log`, Build
  `setup/logs/uwa-wrist-focus-build-final.log`.
- Native Fokusvergleichsberichte unter`setup/calibration/wrist_focus/test_*`.
  Erster Test nur Einstellungen zurückgesetzt; Folgeprüfung ergänzt den
  notwendigen Autofokus-Trigger und berücksichtigt die verzögerte Vorschau.
  Keine Roboterbewegung, keine Simulation-/Treiberneustarts.

Archivherkunft/API-Rekonstruktion:[Analysebericht](wrist_urcap_analysis_2026-11-10.md).
Für Hand-Auge-Aufnahmen Fokus konstant halten und passende Intrinsics verwenden.
