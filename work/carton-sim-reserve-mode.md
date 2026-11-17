# Simulierter Reserve-Observe-Modus

Status2026-11-17: implementiert/installiert, Policyintegrationgeprüft.
Nutzerauftrag: virtuelleKontaktversuchenichtdurchkonservativeStoppreserven
vorzeitigblockieren; aktuelleReaktions-/Bremsannahmenerklären.

Umsetzung/Bedienung: docs/simulation_stop_reserve_mode.md. AusschließlichTask-
Simulationsquellengeändert, Defaultenforceerhalten; beobachteteReserveund
Verletzungweiterprotokolliert. Geometrie20mm/FCLundKontakt-/Schlupf-/Frische-
Stoppsweiteraktiv. HostsichtvorQuelländerung:keineGreifwelten. KeinRealzugriff,
keinKernelwechsel, keinneuerDrehphysiklauf. FremdegestageteÄnderungenerhalten.

Prüfung:103PythonfällePASS/BuildPASS.600gespeicherteDrehzuständemit5×-Caps,
Reserveenforceblockiert600(min−37,188mm),observe0(min176,277mmüber20mm).
QuelleundversiegelterBerichtsetup/tasks/carton_stop_reserve_mode_20261117/.
Logssetup/logs/uwa-sim-reserve-*.log. BestehendeKraftdatenbleibenunverändert.
