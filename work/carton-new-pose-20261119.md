# Neuer Kartonort,19.11.2026

- Status: vorbereitet, wartet auf ausdrückliche Nutzerfortsetzung;  Hauptagent des realen Kartongreifchats. Nutzer meldet Karton
  umgestellt und setzt beauftragten Wiederholungstest fort. Exklusive rechte
  UR-Ausführung auf N100, keine anderen Arm-/Greiferzugriffe währenddessen.
- Beide rechte Arme zuvor tatsächlich Home, Greifer offen. Neue OAK-Aufnahme
  und neue Objektregistrierung erforderlich, keine alten Objektziele abspielen.
- Bewährten auf N100 laufenden freigegebenen Stand nutzen. Lokal entsteht
  parallel ein Motion-Review-Pilot; nicht ungeprüft deployen/parallel aktivieren.
- Grenzen .1rad/s/.2rad/s²/40mm, genehmigte Trendruhe und nativeStopps gleich.
  Vor hoher Anfahrt gesamte Einfahrt prüfen, dann tatsächliches Bild vor
  minimalem Schließen FOR0/SPE16 ansehen. Danach nur gemeinsame HOLD-Gruppe.
- Daten `setup/tasks/carton_new_pose_20261119/`; Zeitbasis ROSmini getrennt
  von N100-Ausführungsdauer. Nach Umstellung Erfolg erst nach realem Ergebnis.

- Nutzer stoppt Hardware vorübergehend: ausdrücklich nur bis Startbereitschaft
  weiterarbeiten. Ab jetzt keine Programmstarts, Arm-/Greiferziele oder
  Dienstneustarts; vorhandener Erstworkflow bereits bei Registrierung beendet,
  keine Armziele gesendet. Vor Realstart neue Nutzerrückmeldung abwarten.
- Aktuelles Foto13:24:16 zeigt neuen Ort/Rotation; festes rechtes Board nur
  noch4Marker/16Ecken sichtbar, Standard-Neuregistrierung daher korrekt gestoppt.
  Vollständige bisherige Kameraregistrierung gegen aktuelleEcken validiert:
  RMS1,77091px/max2,93326px. ReinOffline-Erweiterung nutzt explizite alte
  Kamerareferenz, keine alteObjektpose. NeueExtrinsicsweiter>=48Ecken;
  Referenzprüfung>=16verteilteEcken/RMS<2/max<4px, keineReferenzketten.
 3gezielteTestsPASS; neueKartonregistrierungmitpassendemROIinArbeit.

## Neuer Kartonort: bis Start vorbereitet, Hardwarepause19.11.2026

- Nutzer meldet umgestellten Karton; während Erkennung stoppt er Hardware und
  erlaubt ausdrücklich nur Vorbereitung bis zum Start. **Keine Programmstarts,
  Arm-/Greiferziele oder Ausführung bis zu neuer Nutzerrückmeldung.** Letzter
  bestätigter Armzustand Home/offen; aktuelle native Bereitschaft nach Pause
  erst vor Ausführung neu prüfen. In dieser Sequenz kein Armziel gesendet.
- Neues OAK-Standardbild13:24:16/Fokus107: Kartonzentrum gegenüber vorheriger
  Pose etwa434,5mm versetzt und15,73° gedreht. Rechtes Referenzboard durch Karton
  teilweise verdeckt. Explizite bisherige vollständige Kameraregistrierung gegen
  aktuelle16Ecken validiert: RMS1,771px/max2,933px. Keine neue Extrinsic aus
  wenigen Ecken, keine alte Objektpose verwendet; globale Kameraprofile gleich.
- `register_carton_from_oak.py --camera-reference-pose ... --planar-texture`
  mit aktuellem Bildausschnitt erfolgreich (`registration-v4/`). Drei akzeptierte
  aktuelle Textur-/Tischauflagefits mit25/25/26Inlier, Unterstützung4,27/5,00/
  4,52px; interne Streuung2,866mm/0,682°. Vorschau visuell geprüft. Keine
  Behauptung absoluter Genauigkeit oder qualifizierter realer Kontakte.
- Konkrete Visionkorrektur: planare Modellfeatures über Homographie-Konsens
  auf entzerrten Pixeln vor IPPE bewerten, statt vorab allein EPNP zu verlangen;
  bestehende Positivtiefe-/Mehrdeutigkeits-/RMS-/Inliergrenzen erhalten. Opt-in
  affine Merkmalsansichten und panelweise Zuordnung, Ergebnisse im Originalbild
  prüfen.8gezielteTracking-/ReferenztestsPASS. Alte Fehlversuchev1–v3 erhalten.
- Vollständige hohe Anfahrt UND nachfolgende offene Einfahrt geometrisch gültig.
  Auch tatsächliche serielle RF/RR-Vorpositionsbahnen mit Zeitparametrierung
  offlinePASS (`high-offline`: OFFLINE_CHECKED_NOT_EXECUTED); Einfahrt-Ausführer
  offlinePASS (`entry-offline`: OFFLINE_ENTRY_RECHECKED). Beide Ellbogen im
  Ziel etwa1,486m über Welt0, Tisch0,9m; gewünschte negative Ellbogenzweige.
  Reine nominale hohe Motorbahnen35,22+32,18s, keine gemessene Ausführungszeit.
- Auf zuletzt tatsächlich gemessenen Homezustand vor Nutzerstop gebunden;
  vor echtem Start weiter frische Start-/Halt-/Offenprüfung ohne Grenzlockerung.
 0,1rad/s/0,2rad/s²/40mm/Trendruhe unverändert. Aktueller N100-Stand genutzt;
  paralleler lokaler Motion-Review-Pilot nicht ungeprüft deployt oder aktiviert.
- Daten `setup/tasks/carton_new_pose_20261119/`, `prepared.json`, `pose-preview.jpg`;
  N100 gleichnamig unter `~/uwa-ur-runtime/`. `execute-prepared.sh` nur als
  Datei vorbereitet, NICHT gestartet. Es endet nach offener Einfahrt; tatsächliche
  neue Einfahrtaufnahme muss vor FOR0/SPE16-Schluss geprüft werden. Danach nur
  gemeinsame Objektgruppe/HOLD. Keine geladene unabhängige Armfahrt.
- Dieser Vorbereitungsabschnitt enthält Visionentwicklung und Hardwarepause,
  ist kein repräsentativer vollständiger Griffzeitlauf. Details im Arbeitsstand
  `work/carton-new-pose-20261119.md` im Zellrepo.
