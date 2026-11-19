# Gemini-Test starten und auswerten

Stand 19.11.2026. Der zweite Test fragt, ob ein frischer Agent eines
anderen Anbieters den vorhandenen Planer aus der Übergabe bedienen kann.
Die Fläche bleibt vertraut, der Radius beträgt diesmal 22 mm. Die Aufgabe
prüft zugleich, ob der Agent die Greifgeometrie im HTML-Modell korrekt
einordnet. Der erste Agent musste die Gegenwand noch im Modellcode
ergänzen. Ein Vergleich mit seinen 18:55 Minuten beschreibt folglich
die beiden Abläufe mit unterschiedlichen Toolkit-Ständen.

## Empfohlener Start im VS-Code-Terminal

Die Antigravity CLI 1.5.12 liegt bereits im Workspace. Der Binärdownload
wurde gegen die SHA512-Prüfsumme aus Googles Manifest geprüft.
Für persönliche Konten ist Antigravity der Nachfolger von Gemini CLI
und Gemini Code Assist. Google AI Pro und Ultra verwenden die
Antigravity-Kontingente des angemeldeten Kontos. Credits eines
AI-Studio-API-Projekts gehören stattdessen zum API-Zugang.
[Googles Umstiegshinweis](https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals) ·
[Antigravity-Kontingente](https://antigravity.google/pricing) ·
[Anmeldung und API-Zugang](https://antigravity.google/docs/install?tab=cli)

1. Im integrierten Terminal einmal die CLI starten und dich mit dem
   Google-Konto anmelden, auf dem dein Kontingent liegt.
   Dazu die CLI aus ihrem Werkzeugordner öffnen, anschließend wieder verlassen.
   Login und Browserfreigabe finden vor der Testaufzeichnung statt.

   ```bash
   cd /home/rosmatch/UWA_ws/setup/agent_tools/antigravity
   ./agy
   ```

2. Mit `./agy models` den Namen eines verfügbaren Gemini-Flash-Modells
   prüfen. Beim Starter nach Wunsch `--model MODELLSLUG` anhängen.
   Ohne Vorgabe nutzt der Client sein aktuell gewähltes Modell.
   [CLI-Referenz](https://antigravity.google/docs/cli/reference/)

3. Den vorbereiteten Test starten. Der Starter öffnet im Zell-Repo eine
   neue CLI-Unterhaltung mit dem Prompt und einem eindeutigen Trialpfad.
   Toolabfragen im normalen Berechtigungsmodus einzeln prüfen und im
   Aufgabenumfang freigeben. Wenn ein Tool blockiert, die Meldung als
   Testbefund festhalten. Nach der Abschlussmeldung die CLI verlassen,
   damit der Starter die Sitzungsdauer und den Exitcode speichert.

   ```bash
   cd /home/rosmatch/UWA_ws
   python3 src/multi_arm_manipulation_UWA/tools/start_gemini_trial.py
   ```

Wenn dein Guthaben in **AI Studio** liegt, verwende den in Googles
Authentifizierungsanleitung beschriebenen Provider `gemini` und
`GEMINI_API_KEY`. Anmeldedaten gehören weder in den Prompt noch
in die aufgezeichnete Sitzung.
[Google-Anleitung für den API-Schlüssel](https://antigravity.google/docs/install?tab=cli#using-a-gemini-api-key)

## Alternative mit VS-Code-Erweiterung

Die offizielle Erweiterung **Google Antigravity** von Google ist im
Marketplace verfügbar. Installieren, anmelden, das Zell-Repo öffnen und
eine neue Unterhaltung mit Gemini Flash wählen. Den Starter mit
`--prepare-only` ausführen und den vollständigen Inhalt des ausgegebenen
`prompt.md` einfügen. Der Pfad im Prompt ist für diesen Lauf eindeutig.
Beim Test in der Erweiterung steht der Terminalmitschnitt des Starters
nicht zur Verfügung. Den sichtbaren Chat bei Bedarf separat exportieren.
[Offizielle VS-Code-Anleitung](https://antigravity.google/docs/ide/extensions/vscode/)

## Protokoll und Abnahme

- [Originalprompt](PROMPT_GEMINI_TRIAL_02.md) und
  [Agentenübergabe](GEMINI_HANDOFF.md) stehen im Repo. Der Starter legt
  Kopien mit Hashes und den tatsächlichen Prompt im Sitzungsordner ab.
- Der Starter gibt den Ordner unter
  `setup/agent_trials/box_gemini_20261119/session-*/` aus.
  `observer.json` erfasst CLI-Version, Modellvorgabe, Start, Ende und
  Exitcode. `terminal.log` und `terminal.timing` enthalten sichtbare
  Terminalausgabe und deren Zeitabstände. Die Aufzeichnung endet beim
  Schließen der CLI. Sichtbare Ausgabe kann Kontoangaben enthalten. Beim
  Weitergeben nur die dafür geeigneten Dateien oder eine bereinigte Kopie
  verwenden.
- Unter `trial/` entstehen Bericht, Stufenzeiten, Befehlsausgaben und
  Modellartefakte. Die Sitzung ab CLI-Start und die gemessenen Agentenstufen
  überlappen. Falls Gemini keine Stufen erfasst, bleibt die Sitzungszeit
  belegt und der fehlende Teil ein Testbefund. Modelllaufzeit separat lesen.
- Für die Auswertung den ausgegebenen Ordner verwenden. Relevant sind
  richtiges Modell/CLI, Zeit bis zur ersten Vorschau, Rechenzeit und
  Stufenwandzeiten, Fehler und Hilfen, erwartete Flächen/22-mm-Radius,
  Audit und richtige Einordnung der Kontaktgeometrie. Freigabewartezeit
  als solche ausweisen. Tokenwerte nur übernehmen, wenn der Client sie
  tatsächlich anzeigt. Die Protokolle erfassen keine interne Denkzeit.

Die Anmeldung und der echte Kompatibilitätstest werden durch die
Bedienperson gestartet. Der Testumfang ist der Offline-Pilot.
