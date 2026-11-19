# Zweiter Agententest mit Gemini

- Status: Vorbereitung abgeschlossen, 2026-11-19 (Australia/Perth), Codex dieses Chats.
- Auftrag: Greifhöhen-Abgleich dauerhaft verankern und einen neuen Test
  für einen Drittagenten vorbereiten. Gewünschter Client ist Gemini.
- Bereiche: Projektregeln, Pilotdokumentation, Agentenübergabe,
  lokaler CLI-Start und Trace unter setup/agent_trials/.
- Der Test verwendet ausschließlich das gespeicherte Kinematikmodell.
  Es sind keine Geräte-, Dienst- oder Simulationsaktionen vorgesehen.
- Projektregel und Pilotdokumentation verlangen einen gemeinsamen
  Greifbezug. Gemini-Auftrag und Handoff unter docs/agent_trials/.
- Lokale CLI 1.5.12 aus SHA512-verifiziertem Google-Release.
  Der Starter erzeugt frischen Prompt und Sitzungsprotokoll. CLI-Startpfad
  und Exitcode-Erhalt mit simuliertem Client geprüft. 22-mm-Modelltest
  einschließlich separatem Audit bestanden. Google-Anmeldung und
  eigentlicher Gemini-Lauf starten durch den Nutzer.
