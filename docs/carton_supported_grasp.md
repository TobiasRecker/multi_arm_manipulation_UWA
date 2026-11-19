# Karton greifen: kurzer realer Ablauf

Aktuell19.11.2026,13:01: Beide rechten Greifer halten den aufliegenden Karton
nach Wiederholung über den N100. Abschlussprüfung PASS, beide OBJ2 und frischer
statischer Endhalt bestätigt. Gemeinsamer virtueller Objektframe eingefroren;
jetzt nur HOLD, keine unabhängige Armfahrt und keine automatische Erholung.
Das positionsbasierte Ruheprofil ist aktiv und auch für künftige Kartonabläufe
vom Nutzer freigegeben. Seit letztem Home rund19min05s inklusive Softwarefehler
und Korrekturen, kein störungsfreier Zeitbenchmark. Nachweise/aktueller Zustand
im HANDOVER und `work/carton-cycle-n100-20261119.md`.

UR-Treiber/Guard/Greifer/Executor jetzt auf N100 `~/uwa-ur-runtime`, Domain66/
LOCALHOST; GUI auf ROSmini mit`--n100`. Keine parallelen ROSmini-Hardwaredienste.

## Normaler Bedienablauf

1. **UWA Robot Power → Start + ROS** startet die Betriebsanbindung. Das Fenster
   darf danach geschlossen werden; es ist keine laufende Testreihe. Falls die
   Treiber neu angelegt wurden, die vorhandenen Haltecontroller einmal provisionieren.
2. Ein aktuelles OAK-Foto und einen aktuellen Armzustand aufnehmen. Die Kartonpose
   direkt über das sichtbare feste rechte Tischboard bestimmen. Vorhandene
   Basisanbindungen und globale Kameraprofile bleiben unverändert.
3. Vor der Realanfahrt auch die gesamte folgende Einfahrt am geplanten hohen
   Zustand prüfen. Aufgabengerechte Konfiguration wählen (RF hier mit negativem
   physischem Ellbogen); Referenzseeds dienen frischer IK, nicht dem Replay.
   Die hohen Vorpositionen mit **0,1rad/s** anfahren. Nur der jeweils fahrende
   Arm wird freigegeben; die anderen behalten ihre Haltezustände. Greifer an
   diesen freien hohen Positionen aktivieren und offen bestätigen.
4. Mit offenen Backen ausrichten und in die Greifstelle einfahren. Die
   Kartonhülle ist nur in diesem Zustand mit der tatsächlichen offenen
   Greifergeometrie geprüft; es gibt keine Arm/Karton-Touchausnahme.
5. Das reale Einfahrbild ansehen und beide Greifer mit **FOR0/SPE16** schließen.
   Danach nur halten: keine unabhängigen Armziele, kein Hub und kein Transport.

Es gehört keine separate Simulations-, Kraftmess- oder Diagnosereihe in diesen
Bedienablauf. Bei einem technischen Abbruch bleiben die Arme gestoppt und die
Greiferziele erhalten. Es gibt keine automatische Neustart-/Öffnen-/Rückfahrserie.
Die vorhandene Kollisions-, Datenfrische-, Halte- und native UR-Sicherheit bleibt
aktiv. Armweise Freigabe und reale offene Einfahrt sind seit19.11. praktisch
bestätigt. Der aktuelle statische
Greifschluss mit Trend-Ruheprofil ist bestanden; Tragfähigkeits-/Kraftqualifikation
und geladene Hardwarebewegung bleiben offen.

## Bausteine für Agenten

Aus dem Workspace zunächst `source src/multi_arm_manipulation_UWA/scripts/control_env.bash`.
Das feste Fahrprofil ist `uwa_cell_motion/config/hardware_carton_supported_trend.yaml`;
keine alten Langsamprofile übernehmen.

| Aufgabe | Werkzeug | Vorgabe |
| --- | --- | --- |
| Aktueller nativer Foto-Frame | `oak4_photo.sh capture --mode standard --focus 107` im OAK-Repo | Bestehende Kamera-Lease, passende107-Optik |
| Arm-/Greiferzustand lesen | `tools/prepare_carton_hardware.py --observe --output ...` | Nur lesender Snapshot; sein historisches Commissioning-Profil ist kein Fahrprofil |
| Geometrie und Griffrezept einfrieren | `tools/prepare_carton_recipe.py --output ...` | Direkt aus versioniertem Kartonasset, keine alten Simulationsverzeichnisse |
| Objektpose schätzen | `tools/register_carton_from_oak.py` | Natives Foto, Metadaten,107-Intrinsics und aktuelle `hardware.urdf` aus dem Rezept |
| Hohe Ziele planen | `tools/prepare_carton_pregrasp.py` | Aktuelle Beobachtung, neue Objektpose, `contacts.json`, `scene.json`, Fahrprofil |
| Hohe Ziele anfahren | `tools/run_carton_pregrasp.py --execute --reset-unloaded` | Optional einmalig `--start-ros-programs`, keine Safetyquittierung |
| Greifer vorbereiten | `tools/carton_gripper_phase.py prepare --state HIGH/result.json --output ... --execute` | Hohe Vorpose und gehaltene Arme; shared API vorher explizit enable |
| Offene Einfahrt planen | `tools/prepare_carton_open_entry.py --evidence HIGH_PLAN --approach HIGH/result.json --output ...` | Gemeinsamer Objektframe, keine Kollisionsausnahmen |
| Offene Einfahrt ausführen | `tools/run_carton_open_entry.py --plan ENTRY_PLAN/result.json --output ... --execute --reset-unloaded` | Keine Schließ- oder Hubziele |
| Statisch schließen | `tools/carton_gripper_phase.py close --state ENTRY/result.json --output ... --execute --visual-confirmed` | Agent hat das tatsächliche offene Einfahrbild geprüft |

Die eigenen Hardware-/Greiferdienste schützen ihren Arbeitsspeicher gegen Swap;
das ändert weder Fahrgrenzen noch Kollisions-/Stoppkriterien. Ihre Startskripte
berühren keine fremden Simulationen.

Die Werkzeuge verwenden jeweils ein neues Ausgabeverzeichnis. Ohne `--execute`
sind die Ausführungswerkzeuge offline bzw. lesend. `--visual-confirmed` hält die
bereits zum Ablauf gehörende Bildentscheidung fest, fordert aber keinen weiteren
Bediener-Freigabedialog an. Der gemeinsame Greiferdienst wird mit
`scripts/grippers.sh enable max_force_raw:=0 max_speed_raw:=16` bereitgestellt;
dieser Dienststart selbst aktiviert oder bewegt keine Finger.

`register_carton_from_oak.py` erhält `--image`, `--metadata`, `--intrinsics`,
`--description`, `--output`. Der aktuelle107-Kandidat liegt ausdrücklich unter
`setup/calibration/oak_capture_proposal_20261118/calibration_candidate_v1/oak_pose_candidate.json`.
Er wird nicht global übernommen. Die Pose nutzt die sichtbare Tischauflage als
Estimatorprior und prüft deren Bildrestfehler gegen die unveränderten
Registrierungsschwellen. Die vorgegebenen Bildausschnitte gehören zum bekannten
rechten Kartonplatz; bei LOST keine alte Pose stillschweigend weiterverwenden.

## Belege und Grenzen

Vorbereiteter Offline-Stand:
`setup/tasks/carton_grasp_20261118_offline_finish/` mit `recipe-v2/`,
`registration-v2/`, `high-plan-v2/` und `entry-plan-v2/`.
Die zukünftige hohe Startposition ist ausdrücklich **geplant, nicht aktuell**.
Vor echter Ausführung werden Modellbindung und tatsächlicher Start geprüft;
ein Plan ist nach einem Neustart keine automatische aktuelle Zustandsmessung.

Die reale mehrlagige Wand ist nicht als exakte CAD-Geometrie vermessen. Die
Einfahrt verwendet deshalb eine35mm-Wandhülle und5mm-Randerweiterung als
**Designannahme**, ohne den bestehenden40mm-Nachbarabstand zu reduzieren.
Native Wrench-Änderungen während offener Einfahrt brechen den Ablauf ab;
sie sind keine Messung der Backenklemmkraft. FOR0 ist die minimale Rohkrafteinstellung,
keine physikalische0N- oder garantierte50N-Grenze. Die Nutzerangabe lautet500g
und50N je Backe/Wandfläche. OBJ2 unterstützt die Kontakterkennung, beweist aber
keine vier Auflagekontakte und keine Tragfähigkeit.

Beim Schließen werden ein gemeinsamer virtueller Objektframe und feste
Objekt→TCP-Offsets der bestätigten Mitglieder gespeichert. Erlaubte nächste
Aktion ist ausschließlich **HOLD**. Der tragende gekoppelte Hardwareexecutor
für spätere Objektbewegungen bleibt separate Arbeit; der unabhängige PTP-Runner
wird dafür nicht verwendet.

## Eng begrenzte Softwarekorrekturen19.11.

- Bestehende20Hz-Nativdaten werden im Aufgabeprofil20Hz statt10Hz weitergegeben;
  alle Alters-/Kollisions-/Stoppgrenzen und0,1rad/s bleiben erhalten.
- FOR vor SPE einzeln rückbestätigen, erst danach POS/GTO. Aktiviertes OBJ0 mit
  POS≤8/COU0 nur für Öffnen an hoher gehaltenenPose akzeptieren; Einfahrt und
  Schließen verlangen weiterhin bestätigten offenenOBJ3-Zustand.
- ALIGN und ENTRY proArm in einer Action mit unveränderten Einzelzeitgesetzen,
  ohne erneute Geometrie-/Controllerübergabe während eigener Aktivierung.
- Kontaktmitglieder vor letzter Armprüfung speichern: ein Programmstopp macht
  einen real geklemmten Karton nicht wieder zu einem unbeladenen Fehlerzustand.

## Konfiguration vor Zahlen vergleichen

Beim aufrechten Tischkarton RF im zuvor erfolgreichen physischen Ellbogenzweig
planen. Andere Zweige nicht nur wegen kurzer Jointdistanz wählen. „Ellenbogen
unten“ und „Wrist innen“ sind kontextbezogene Nachteile; Nachbarabstände,
Gelenkreserven, skalierter Jacobian und Weg werden danach ausgewiesen.
Rezept enthält bewährteIK-Startwerte mit Herkunft; Ziele werden aus aktueller
Bildpose frisch gelöst und geprüft. GanzeEinfahrt VOR hoherReal-Anfahrt prüfen.
`run_carton_cycle.py` protokolliert diese normalen Phasen und hält vor dem
Agent-Bildcheckpoint an; kein automatischer Wiederholungs-/Recoveryloop.


Bei explizit beauftragtem regulärem Programmstart vor dem Schließen bietet
`carton_gripper_phase.py close --start-ros-programs --execute --visual-confirmed`
den geprüften Weg: sämtliche Schnittstellen vorher aufbauen, alle vier Greifer
offen und alle Arme frisch stationär/gehalten/normal bestätigen, dann vorhandenen
unbeladenen Startpfad verwenden. Keine Freigabe nach Kontakt, keine Quittierung
nativer Sicherheitsmeldungen. Der Standard sendet weiterhin kein Play.
Greiferstatus liest persistent über dieselben RPC-Endpunkte jeweils neu vom Gerät.
