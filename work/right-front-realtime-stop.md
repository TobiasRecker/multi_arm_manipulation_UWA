# RT-Stopptest right_front

- Status: **abgeschlossen – Grenze aktiviert und abschließende Messung bestanden**,
  2026-11-17 (Australia/Perth), Hauptagent dieses Chats.
- Nutzer beauftragte erst Vorbereitung, dann Durchführung am vorderen rechten UR
  192.168.8.103. Freie/unbeladene Übergabe und Not-Halt-Zugriff bestätigt;
  nötiger ROS-Programmstart aller vier URs zusätzlich ausdrücklich genehmigt.
- Nach erstem Geschwindigkeitsstopp Nutzerauftrag: überwachte Grenze0,1rad/s.
  Aktiv: `uwa_cell_motion/config/hardware_right_front_stop_test.yaml`, nur RF-q6
  0,1rad/s, übrige23Achsen0,003; Fahrkommando0,003/a0,006 unverändert. Bestehende
  5%-Toleranz einschließlich Reserve erhalten. V2-Körper-/Achsreserve und FCL
  frisch geprüft; keine Änderung an40mmPuffer/Frische/10Hz/1s/0,2rad/s².
- Endzustand: vorhandener Schutzdienst scharf mit obigem Profil. RF im Supervisor
  gehalten/verriegelt; alle4 stationär/RUNNING/NORMAL, ros.urpPLAYING und Reverse
  verbunden. Keine Rückfahrt oder Freigabe nach letztem Test. Kameraansicht,
  Treiber und Simulationen erhalten; keine Power-/Brake-/Greiferaktion.

## Versuche und Nachweise

- Vorbereitung02: nur Modell/Nativebeobachtung,235damaligeTests/BuildPASS.
- Versuch03: ursprüngliches Profil; reale kleine q6-Bewegung, Guard SPEED LIMIT
  0,004729>0,003rad/s vor absichtlichem Trigger. Unglätteter500HzPeak0,021313.
  Keine Reaktionsmessung. Nachher unabhängig alleArme stationär bestätigt.
- Versuch04: geändertes Profil; beabsichtigter Stopp ausgelöst/ACKtrue, keine
  Guardfaults. Recorder behandelt Action-Cancellation als Fehler und endet nach
  49,9ms. Bremsmetriken bleiben null, Fehlerstatus bleibt erhalten.
- Recorder korrigiert: passender eigener Actionabbruch führt zur vollständigen
  passiven Nachbeobachtung, Ack/Hold/Latch/QuietWindow zwingend. Neue Schutz-,
  Frische-, Observer- und sonstige Actionfehler bleiben FAIL. Effektive optionale
  Commandgrenze zusätzlich≤0,003 geprüft.29gezielteRegressionen/py_compile/
  diffcheckPASS, separate Quellenhashes unter04/source-fix-after-attempt04.json.
- Versuch05: **PASS**, voller500Hz-Nachlauf bis940,8ms.20%-Geschwindigkeitsabfall
  ab14,79ms, erstes20msFenster mit allenAchsen≤0,0002rad/s ab30,86ms;
  strenge Stillstands-/Hold-/Latchbestätigung939,23ms. EigenerStopACKtrue,
  keineGuardfaults, RF bleibt gehalten. Vorstopmedian0,001728rad/s; langsamer
  Einzellauf, keine allgemeine Reaktions-/Bremsgrenze. Q6-Nettonachlauf4,77µrad
  unterEncoderstreuung, keine genaue Bremsstrecke daraus ableiten.
- NativeGeräteschritte2ms, gesamteEmpfangslücke im05Laufmax22,41ms; keine
 2msEnd-to-end-Garantie.03/04Originale nicht als bestandene Läufe umgeschrieben.
- UnabhängigeRohdatenprüfung:31msistnurdieerste20msNiedrigphase; danachkurze
  q6-/q5Schwellenüberschreitungenbis175,7/384,8ms. Durchgehendniedrigbis
  Aufnahmeendeab386,84ms, strengesQuietWindow390,78–936,90ms. KeinBeleg,
  dassdiephysischeBremsung939msdauerte; NachweisfensterundJittertrennen.

Artefakte: `setup/realtime/right-front-stop-20261117-{02,03,04,05}/` im Workspace.
Bedienung und Grenzen: `docs/right_front_realtime_stop_test.md`. Aktiver Dienst
`uwa-hardware-motion.service`, Profilwechsel geordnet mit bestätigten Holds;
Anlaufverifikations-/Watchdogstopps dokumentiert. Keine offenen eigenen Geräte-
oder Dienstneustarts, kein weiterer Realversuch geplant.
