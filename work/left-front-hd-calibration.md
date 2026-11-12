# Native HD-Kalibrierung vorne links

- Status: **in Arbeit**, 2026-11-12, Hauptagent LF-HD.
- Nutzer beauftragt nach bestandener VGA-Kalibrierung getrennte native HD-Reihe.
- Erst Kamera-only: CB3 i686/Linux3.14/Python2.7 ohne gcc; nativen V4L2-Helfer
  prüfen, bestehende Sicherung/Rückstellung beibehalten. UCC1.11.1, Kamera
  028E1F350009061C, VGA-Fokus245 manuell unverändert sichern.
- Andere Aufgaben right-rear-hd-intrinsics und Karton-Rekonstruktion erhalten;
  keine fremden Dienste, Treiber oder Kameratransaktionen berühren.
- Neue Daten unter setup/calibration/hardware_handeye/left_front_hd_20261112/.
  Kein Mischen mit VGA, kein automatisches Aktivieren. Neue Bewegungswege nur
  nach vollständiger Prüfung und konkreter Freigabe.

## Nachweise und nächster Schritt

- 17:24 AWST: echtes 2592 × 1944 MJPEG am CB3 im Testburst bestätigt; Fokus
  245, Belichtung 60590, Gain 19 aus V4L2 im Burst; originale vollständige
  Einstellungen und `Normal` danach identisch. 16 Kameratests bestanden.
- Eigener Kamera-ROS-Dienst `uwa-left-front-wrist-hd.service` läuft; kein
  Hardwaretreiber neu gestartet. Erste Probe `records/sample_000.json` mit
  24/24 Ecken und bestätigtem Stillstand in eigener HD-Sitzung aufgenommen.
- 17:27: reversierte Route aus der aktuellen Pose neu aufgebaut, keine diagonale
  Ausnahme. 40 Segmente / 3607 Punkte / 354,6 s reine Fahrzeit. Plan-ID
  `fe91d21b7b68be1dd2091689dd93675210a3f62f22225f4c45a8cc4113c4cb11`;
  realer `--check-only` erfolgreich. Vorschau `uwa-left-front-hd-preview.service`
  auf Domain 69 geöffnet. Andere Arme müssen während dieser Serie stehen.
- Konkrete Freigabe angefragt. Keine Bewegung gesendet. Nach Freigabe nur
  genau diese Route mit frischem Start-/Statuscheck ausführen, dann eigenen
  Fahrcontroller deaktivieren, Fit/Prüfbilder und relative Basislage auswerten.
- Parallel ist RR-HD inzwischen separat freigegeben und der Start vorgesehen.
  Diese LF-Route hat absichtlich keine Diagonalausnahme; LF-Bewegungsstart erst
  wenn RR-Reihe beendet oder deren Nichtstart verlässlich geklärt ist, dann
  aktualisierte reale Fremdarmpositionen neu gegen die ganze Zelle prüfen.

- Benutzer hat die 40 LF-Fahrten konkret freigegeben. Erneuter Start- und
  Modellcheck PASS. RR-Reihe zu diesem Zeitpunkt ohne laufenden Aufnahmelauf.
  **LF beginnt jetzt; RR während LF nicht starten.** Alle drei Nachbararme
  in der LF-Serie durchgehend auf Stillstand überwacht.
- 17:35: LF-Stillstands-Guard erkannte die parallel gestartete RR-Reihe beim
  fünften Abschnitt. LF-Trajektorie wurde abgebrochen, eigener Controller
  inaktiv bestätigt; native Safety NORMAL, External Control verbunden.
  `sample_000` bis `sample_004` vollständig akzeptiert, keine Rückfahrt.
  LF ruht bei ~89,28 % desselben Abschnitts (nur 0,0491 rad zum Ziel;
  ~0,00015 rad Abweichung von der freigegebenen Gelenkgeraden). LF wartet auf
  Ende der RR-Reihe; kein weiterer Befehl an RR. Original und Logs erhalten.
- 17:41: Vorprüfung Reststrecke (nur Vorhersage der RR-Endpose) über 3118
  Punkte kollisionsfrei. Passiver Dienst `uwa-left-front-hd-resume-check`
  wartet auf Ende des RR-Prozesses und inaktive Fahrcontroller, erzeugt
  `resume_same_path` mit real gemessenen Posen und ruft nur `--check-only` auf.
  Kein unbeaufsichtigter Fahrstart. Die anschließenden 35 Wege bleiben exakt
  gleich; nur Abschnitt 005 wird entlang des freigegebenen Wegs gekürzt.

- Nutzer beauftragt Fortsetzung. RR beendet, beide Fahrcontroller inaktiv
  gemessen. Live-Restprüfung erfolgreich: 36 Abschnitte, 3095 Punkte,
  verkürzter Abschnitt 005 auf Originalgerade, alle folgenden Wege identisch.
  Nutzerfreigabe gilt für denselben Weg. Nur LF startet erneut.
- 18:08: zweiter Abbruch, diesmal beim Abschnitt 015 durch External-Control-
  Verlust. Treiber protokollierte unmittelbar vorher 56-ms-Zyklus statt 8 ms;
  Zusammenhang zeitlich beobachtet, Ursache nicht bewiesen. Native Safety
  NORMAL, geladenes `ros.urp` STOPPED, keine automatische Safetyquittierung.
  15 akzeptierte native Datensätze. Eigenen alten RViz-Preview beendet.
- Geladenes `ros.urp` einmal per vorhandenem ROS-Play gestartet, Stillstand,
  Normal und Link bestätigt. Beim Reconnect reaktivierten eigenen Fahrregler
  vor Planung deaktiviert. 26 Abschnitte / 2038 Punkte erneut mit allen vier
  Live-Stellungen geprüft, erster Weg nur unbefahrener Teil der ursprünglichen
  Gerade. Danach freigegebene Reihe erneut bei sample_015 fortgesetzt.
