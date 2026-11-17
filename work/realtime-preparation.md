# Echtzeit-/Wächter-/Reaktionskettenvorbereitung

Status2026-11-17: vorbereitet, dokumentiert und installierteTaskänderungen geprüft.
NutzerauftragumfasstVorbereitung,keineSystemumstellung/Realbewegung.

Hostaudit/Dryrun/Pythonbasisprobe,SimGuardrate+Timing,25/50/100HzKandidaten,
passiverRecorderundstrikteOfflineKettenanalyse. Anleitungen/Annahmen/nochfehlende
Dispatch-/Bremsmesspunkte:docs/realtime_preparation.md. VorQuelländerungHost-
Prozesssichtgeprüft:keineGreifwelt. FremdeHardware-/Glättungsarbeitnichtgeändert.

121TasktestsPASS/BuildPASS; nachersterCollectionneuesparallelesModulgebaut.
Mock67RecorderintegrationPASS,198Guardpakete.300OfflineGeometriefällemax4,813ms.
Artefakte setup/realtime/preparation-20261117/, Logsuwa-realtime-prep-*.
KeineRT-/Hardwarequalifikation; bisherigeStopannahmenbleibenerhalten.

## Installation im ausdrücklichbeauftragtenFolgeschritt

2026-11-17: Ubuntu-RT7.0.0-43-realtimeundrt-testsinstalliert, Signatur/Initrd/
GRUB/defaultRT/PREEMPT_RT/dpkgPASS. PAMundsystemdLimits99/unlimitedfürrosmatch
undvierUR-Diensteinstalliert; frischePAM-Sitzunggeprüft. KeinePrioritätaktiver
Prozessegeändert, keinReboot/Robot-/Dienstrestart. Generic43/42erhalten.
NutzerkündigtNeustartbereitschaftnoch an. Logs/Backups/Dateimanifest
setup/realtime/installation-20261117/, detailsdocs/realtime_preparation.md.
