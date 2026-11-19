# Erster Live-Start aus der Programmbibliothek, 19.11.2026

- Status: am ersten Blocker angehalten, 18:01 AWST. Nutzer möchte den vorhandenen agentenfreien
  Kartonablauf bis zum ersten Punkt testen, an dem er Hilfe braucht, und
  diesen Punkt dann gemeinsam ansehen.
- Bereiche: lokale Programmbibliothek und lesender Startcheck auf dem N100.
  Lokale Optikparameter für den Versuch getrennt halten. Reale Freigaben nur
  über die vorhandene Bedienung, keine Übernahme eines neuen Ausführungsstands.
- Vorabstatus: Arbeitsbereich laut N100-Review-Store freigegeben, keine offene
  Anfrage. Der erste Dateivergleich zeigt unterschiedliche Runner-/Rezepthashes
  und eine fehlende benannte Programmdefinition auf dem N100.
- Ein echter Aufruf der Bibliotheks-API mit separater Optikkonfiguration
  erreichte `live_preflight`. Der N100 meldete abweichende Version von
  `tools/run_carton_cycle.py`. Der Lauf endete vor jeder OAK-, Review-,
  Programmstart- oder Fahrphase. Testserver beendet, keine Übernahme.
  Laufprotokoll `setup/tasks/carton_agent_free_live_20261119/result.json`.
