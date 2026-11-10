# Kartesisches Jogging mit dem MATCH-Regler

Stand: 2026-11-10. Zunächst **right_rear =192.168.8.170**.
Die Roboterrouten laufen nach dem Kabeltausch über Ethernet enp87s0,
PC192.168.8.209. Frühere Funk-Sonderbehandlung ist entfernt; historische
Netzwerkmessungen bleiben als solche erhalten.

## Öffnen und bedienen

Startmenü **UWA Arms**, Rechtsklick-Aktion **Cartesian jog · rear right**.
Alternativ in der GUI genau einen Arm auswählen und **Cartesian jog…** öffnen:

```bash
bash src/multi_arm_manipulation_UWA/scripts/control.sh --mode hardware --arms right_rear --jog
```

Das Öffnen startet weder eine Fahrt noch Power/Brake/Play. Falls der Treiber
noch nicht läuft, im Hauptfenster **Start drivers** wählen.

1. Auf dem UR das passende External-Control-Programm laden. Für hinten rechts
   muss dessen URCap auf **PC192.168.8.209, Port54002** zeigen. Der Port ist je
   Arm unterschiedlich; vorne rechts wäre53002. Netzwerk-/Remote-Einstellungen
   bleiben native UR-Einstellungen, keine zusätzlichen UWA-Freigaben.
2. Falls erforderlich **Prepare UR** zum Einschalten/Bremsenlösen. Danach
   **Start loaded UR program**, damit der UR die Treiberkommandos ausführt.
3. Im Jog-Fenster **Enable jog controller** wählen. Das lädt den vorhandenen
   MATCH-Regler mit dem angezeigten Preset neu und aktiviert ihn.
4. Zunächst kurz einen Achsbutton **gedrückt halten** und loslassen. Translation
   startet bei **0,010 m/s**, Rotation bei **0,100 rad/s**. Einstellbar sind
   0,001–0,030 m/s und 0,010–0,100 rad/s. Achsen beziehen sich auf den
   jeweiligen Roboter-Frame `base_link`, nicht auf RViz-Weltachsen.

Pfeiltasten steuern X/Y, PageUp/PageDown Z; **M** wechselt Translation/Rotation.
Loslassen, **Space**, **STOP JOG**, Fokusverlust oder Schließen senden Null.
Der Dialog sendet während des Haltens mit20Hz, im Leerlauf keinen dauernden
Nullstrom. **STOP** im Hauptfenster stoppt auch offene Jog-Dialoge und deaktiviert
die Bewegungscontroller der betroffenen Arme. Ein Null-Twist ist kein Hardware-Not-Halt.

Die deutliche **JOGGING/STOPPED/CONTROLLER READY/FAILED**-Anzeige bestätigt die
Bedienung. Programm-/Controllerstatus und Subscriberzahl sind informativ;
fehlende Verbindung bzw. native UR-/Treiberablehnung werden angezeigt.
**Save logs** erfasst auch die offenen Jog-Dialoge und das Compliance-Preset.

## Architektur und Nachgiebigkeit

Die Qt-unabhängige Richtungsberechnung wird mit `match_mur_gui` geteilt.
`match_ur_hardware.JogTransport` publiziert `TwistStamped` auf
`/uwa_hardware/<arm>/integrated_cartesian_admittance_controller/equilibrium_twist_cmd`.
Regler ist unverändert `mur_control/IntegratedCartesianAdmittanceController`
mit J-PARSE, kein paralleler Jog-Regler. MuR-Standardparameter bleiben erhalten.

Das UWA-Inventar enthält je Arm `compliance_enabled: false`. Damit sind
`admittance` und `wrench_twist_gain` sechs Nullen, `use_ft_sensor` und
`require_wrench` false. Das Plugin liest Gains in `on_init`; **Enable jog
controller** deaktiviert deshalb Bewegung, lädt dieses Plugin inaktiv neu
und aktiviert es anschließend. Nur ROS-Parameter dynamisch zu ändern würde
die internen Gains nicht aktualisieren. Es gibt zunächst keinen GUI-Schalter
für Nachgiebigkeit. Die vorhandenen Kollisionsalgorithmen wurden erhalten;
das UWA-Profil besitzt weiterhin keine vollständige Zell-Kollisionsprüfung.

Hardware nutzt Domain66, Mock Domain67, Gazebo/RViz Domain64. Das umfasst GUI,
Kindprozesse, Launch und Jog-Transport; Mock darf reale Controller nicht entdecken.

## Prüfnachweise und verbleibender Realtest

- Drei Pakete gebaut: `setup/logs/uwa-jog-build.log`.
- 19 Offline-Tests des Adapters/der UWA-GUI und acht MuR-Kartesik-Tests bestanden:
  `setup/logs/uwa-jog-unit.log`, `uwa-jog-mur-cartesian.log`.
- Isolierter Live-Mock-Test in Domain67: kein Twist beim Öffnen, tatsächlich
  geladene Compliance-Gains null/FT aus, gehaltene Translation bewegt die
  Mock-Gelenke um maximal0,028rad; nach Loslassen0,0rad weitere Drift im
  Messfenster. Rotation und Fokusverlust-Stopp bestanden.
  `setup/logs/uwa-jog-live.json` und `uwa-jog-dialog.png`.
- Am realen, neu geladenen hinten-rechts-Regler sind Gains null/FT aus lesend
  bestätigt: `setup/logs/uwa-jog-hardware-preset.json`. Manager erreichbar,
  Broadcaster aktiv, Bewegungscontroller inaktiv. UR RUNNING/NORMAL/Remote,
  geladenes `ros.urp` beim Prüfen STOPPED:
  `setup/logs/uwa-jog-hardware-after-restart.json`.
- Der Agent hat keine realen Power-/Brake-/Play- oder Fahrbefehle gesendet.
  Die erste physische Jog-Bewegung bleibt der bewusste manuelle Bedienversuch.
- Alle sechs echten Gelenkwinkel hinten rechts erfolgreich gelesen:
  `setup/logs/uwa-jog-hardware-joints.json`. Das funktioniert unabhängig vom
  aktuell STOPPED-Programm. Nutzer meldet URCap-Port50002; lokal lauscht nur54002.
  Route/Ping/Dashboard/Portnachweis: `setup/logs/uwa-jog-network-check.json`.
- Vierarm-Mock-GUI-Regression mit24 Gelenken, Controllerwechsel, Export,
  STOP, Managerexit/Neustart und eigenem Abbau bestanden:
  `setup/logs/uwa-jog-full-gui.log`. Installierte Desktop-Aktion geöffnet und
  sichtbare Fenster geprüft; kein Start zusätzlicher Hardwaretreiber dadurch.
