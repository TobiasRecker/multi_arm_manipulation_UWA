# Kontakt-Simulation: Stoppreserve beobachten statt erzwingen

> Historischer Stand vom 17.11.2026. Seit dem 19.11.2026 wirkt diese Option ausschließlich bei der Offline-Planprüfung. Der aktuelle Gazebo-Start verwendet die regulären Controller ohne die hier beschriebenen Laufzeitwächter.

Stand2026-11-17; ausdrücklicher Nutzerauftrag für virtuelle Dynamikversuche.
Der Taskplaner und sein Laufzeitwächter unterstützen:

```yaml
exploration_mode: true
force_observation: true
simulation_stop_reserve_mode: observe
```

Default ist `enforce`. `observe` verlangt beide Explorations-/Messflags und gilt
nur im isolierten `cell_task`-Simulationspfad (Domain64, LOCALHOST,
Gazebo-Partition `uwa_cell_sim`). Hardwarewächter/-profile wurden nicht geändert.
Eine neue Szene vorbereiten; bestehende SHA-gebundene Szenen nicht umschreiben.
Beispielprofil für die gespeicherte5×-Drehgeometrie unter dem Workspace:
`setup/tasks/carton_stop_reserve_mode_20261117/profile.yaml`.

## Verhalten

`observe` entfernt ausschließlich den geschwindigkeitsabhängigen
Reaktions-/Bremswegaufschlag aus den vom Planer und Laufzeitwächter erzwungenen
Paarabständen. Der20mmModellpuffer und vollständige geometrischeKollisionsprüfung
bleiben aktiv. Kontaktphysik/Kraftmessung, Geschwindigkeitsgrenzen, Kontaktverlust,
Schlupf, Frische, Runnerwatchdog und Greifverbundstopps bleiben unverändert.
Kein künstlichesAnheften, kein automatischesÖffnen nachStopp.

Die Reserve wird weiter mit den gleichen Annahmen gerechnet. Jedes Livepaar
enthält neben dem wirksamen `threshold_m` auch `modeled_stopping_threshold_m`,
`modeled_stopping_reserve_violated` und `stopping_reserve_mode`. Der Guardstatus
führt `simulation_stop_reserve_mode`; Objekttrajektorien und Agentreview zeigen
den Modus. RViz trägt imObserve-Modus ausdrücklich den Text
`EXPERIMENT: STOP RESERVE OBSERVE ONLY`. Der unabhängige Recorder speichert diese Paarfelder samt Modus unter
`stopping_reserve` in jedem Evaluationstrace-Sample.

## Bisherige Annahmen

- Wächter10Hz:100ms biszur nächstenPrüfung.
- Zustandsalter: imPlan maximal150ms; online tatsächlichesAlter.
- Zusätzlich100ms `stop_latency_s`.
- Planung somit350ms, online200ms plusZustandsalter.
- Letztes5×-Profil: angenommene Gelenkbremsverzögerung2rad/s²;
  historischerDefault0,5rad/s². KeinegemessenenUR-Werte.
- Gemeinsamer statischerModellpuffer20mm.

ProGelenk wird `v²/(2a)` für denBremswinkel angesetzt. DieReaktionsbewegung
ist `v·Latenz`; Geschwindigkeiten sind dasMaximum aus gemessenemBetrag und
konfigurierterproDOFHüllgrenze. Linkradien bilden konservativekartesische
Dreiecksungleichungsgrenzen, beideArmbudgets werdenaddiert. Deshalb gibt es
keinen einzigen konstantenBremsweg inMillimetern fürdieganzeBahn.

Beispiel bei0,065rad/s und2rad/s²:32,5msBremszeit und0,001056rad≈0,061°
Bremswinkel. Allein350msangenommeneLatenz ergeben0,02275rad≈1,30° zusätzlich.
DieLatenzannahme dominiert diesesBeispiel. Fingergrenzen gehen ebenfalls ein.

EinEchtzeitkernel alleinändert weder diese10Hz-Prüfung noch die expliziten
Softwarebudgets. UR empfiehlt für seinenROSTreiber Echtzeitfähigkeit:
[offizielle Echtzeitkonfiguration](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_client_library/doc/real_time.html).
E-Series-RTDE kann bis500Hz liefern, kann beiRessourcenmangel aberPaketeauslassen:
[offizielle RTDE-Dokumentation](https://docs.universal-robots.com/tutorials/communication-protocol-tutorials/rtde-guide.html).
FürkleinereRealbudgets müssen vollständigeZustands-/Prüf-/Kommandolatenz und
beladeneBremsantwort gemessenwerden; Interfacezyklus istkeineStoppzeit.
KeinKernelwechsel undkeineRealbewegung Bestandteil dieserÄnderung.

## Prüfung

103PythonfällePASS, LyricalTaskbuildPASS. Testsbelegen Opt-in-Validierung,
Defaultreserve, gleichePolicy inPlaner/Livepaaren, weiterberechneteVerletzungen
und unveränderteKontakt-/Frischestopps.

Offlineintegration:600Zustände ausdergespeichertenDrehbahn mitdenselben5×-
Gelenkhüllgrenzen. `enforce` weistalle600ab (schlechtesteReserve−37,188mm),
`observe` keine; kleinsterAbstandüberdemweiteraktiven20mmPuffer176,277mm.
Dies isteineabgetastetePolicyprüfung, **keinneuerDreh-Physiklauf** undkein
neuerdichterKollisionsnachweis. Ergebnis/Quelle:
`setup/tasks/carton_stop_reserve_mode_20261117/{result.json,check.py}`.
Logs: `setup/logs/uwa-sim-reserve-{tests,build,integration}.log`.

## Folgeschritt vorbereitet

[Kernel, höhere Prüfraten und Reaktionsmessung](realtime_preparation.md):
Hostaudit,25/50/100HzSimulationskandidaten und passiverRecorder stehen bereit.
Die350ms oben betreffen dieSimulation; realeProfile haben eigeneAnnahmen.
