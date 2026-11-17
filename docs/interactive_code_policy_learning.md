# Kooperative Code-Policies mit interaktivem und langfristigem Lernen

Stand17.11.2026, Australia/Perth. Konkretisierung des
[Pipeline-Reviews](programming_pipeline_lbd_review_2026-11-17.md) nach
Nutzerpräzisierung. Dies ist ein Entwicklungsentwurf, keine implementierte
Lernplattform und kein neuer Simulations-/Hardware-Prüfnachweis.

## Nutzerziel und Abgrenzung

Ein schnelles einfaches LLM entwickelt **ausführbare Aufgabenprogramme** für
ein Mehrrobotersystem. Beispiele des Nutzers:

- Zwei Arme drehen den Avocado-Karton auf die Seite und halten ihn; ein dritter
  stellt einen weiteren Karton darauf.
- Zwei Arme halten die Box; ein dritter zeichnet einen Kreis auf jede Seite.

Der32-Aufgaben-/21-Bahnen-Pilot behandelt ausschließlich das separate
Kollisionsvermeidungsproblem. Er ist weder Trainingsdatenbasis noch
Fortschrittsmaß des hier beschriebenen Aufgabenlernens. Kollisionsplanung wird
als vorhandener Unterdienst verwendet.

Nutzer bevorzugt eine Simulationsvorführung durch den Agenten mit anschließendem
sprachlichem Feedback oder direkter Teleopkorrektur. Handführungsbeispiele
bleiben für schwierige Teilprobleme interessant. Der Unterstützungsbedarf soll
nicht allein davon abhängen, dass der Agent ihn selbst zuverlässig erkennt.
Zusätzlich soll das System über viele Ausführungen aus eigenen Ergebnissen
lernen, insbesondere für wiederkehrende Industrie- und Bauaufgaben.

## Das Lernprodukt ist ausführbarer Code plus Erfahrung

Das Programm beschreibt Rollen, Abfolgen, Schleifen, Bedingungen und
Fehlerreaktionen. Vorhandene Bibliotheken übernehmen Wahrnehmung, Geometrie,
Trajektorien, Kontaktregelung und Gerätekommunikation. Eine Aufgabenbeschreibung
kann die Generierung strukturieren; der Nutzeransatz bleibt **Code as Policy**.
Neue Skills dürfen in der Entwicklung entstehen. Bekannte Routinen sollen
später direkt wiederverwendet werden und weniger LLM-Arbeit benötigen.

Die Aufgaben benötigen eine explizite Beschreibung von:

| Aspekt | Beispiel |
|---|---|
| Rollen und Ressourcen | Haltegruppe, Arbeitsarm, Werkzeug, Teil1 und Teil2 |
| Objektbezogene Geometrie | Boxfläche als Bezugsframe des Kreises; Auflagefläche als Bezug der Stapelpose |
| Gleichzeitigkeit | Haltegruppe hält während Bearbeitung; Umorientierung erst nach Werkzeugrückzug |
| Kontaktphasen | freier Anflug, Ansetzen, Bearbeiten/Ablegen, Lastübernahme, Rückzug |
| Messbedingungen | Teil tatsächlich ruhig, Werkzeug frei, Teil2 unterstützt, Zeichnung vollständig |
| Varianten | andere Boxpose, Abmessungen, Werkzeug oder Material; Geltungsbereich des Programms |

Halten bedeutet weiterhin aktive Überwachung der Haltegruppe. Gleiche
Zielzeit oder ein erfolgreicher Bewegungsaufruf allein bestätigt keine stabile
Bearbeitungspose. Gemeinsame Objektsteuerung gilt innerhalb jeder starren
Greifgruppe, nicht pauschal für alle beteiligten Arme.

## Interaktion: erst vorführen, dann gezielt korrigieren

Vorgeschlagener Ablauf:

1. Agent erstellt ein erstes Programm aus Auftrag, aktuellen Fähigkeiten und
   passenden früheren Erfahrungen. Er zeigt die Rollen und angenommenen
   Aufgabenbedingungen verständlich an.
2. Programm in Simulation ausführen. Bewegung, Programmphase, aktive Kontakte
   und Ergebnisprüfung gemeinsam darstellen. Geometrische Modellanimation
   und Kontaktphysik getrennt kennzeichnen.
3. Nutzer kann eine Stelle markieren und kommentieren, pausieren oder die
   Kontrolle übernehmen. Alternativ ab gespeichertem Zustand eine korrigierte
   Fortsetzung zeigen. Übernahme und Rückgabe der Kontrolle bleiben explizit.
4. Den Eingriff an Szene, Zustand, Programmversion und Schritt binden. Original
   und korrigierte Fortsetzung erhalten, ebenso Erfolg oder Fehler danach.
5. Agent ändert gezielt Code, Parameter oder einen Bewegungsbaustein und
   führt die Änderung erneut aus. Neue Version gegen den bisherigen Stand
   und bekannte Aufgaben prüfen, dann als nutzbare Erfahrung speichern.

Bei Teleop steuert genau eine Quelle die betroffene Ressource. Für die
Haltegruppe wird das gemeinsame Objekt geführt, für den Arbeitsarm sein
Werkzeug. Automatik darf nicht gleichzeitig weiterkommandieren. Das Verhalten
der anderen Rollen während einer Übernahme gehört zum Programmschritt.
Ein Checkpoint muss bei Kontaktversuchen auch Objekt-/Kontakt- und Reglerzustand
berücksichtigen; allein identische Gelenkwinkel ergeben nicht dieselbe
physische Anfangsbedingung. Wiederherstellbarkeit im gewählten Simulator prüfen.

## DAgger als Vorbild, keine Gleichsetzung

[DAgger, Ross et al., AISTATS2011](https://proceedings.mlr.press/v15/ross11a.html)
sammelt Expertenaktionen an Zuständen, die durch die aktuelle Policy erreicht
werden, aggregiert die Daten und aktualisiert die Policy. Für uns ist der
wichtige Gedanke, Korrekturen unter der eigenen Ausführung zu gewinnen und
nicht nur ideale vollständige Demonstrationen nachzuahmen.

[HG-DAgger, Kelly et al., ICRA2019](https://arxiv.org/html/1810.02890v2)
überlässt dem Menschen die Entscheidung über die Kontrollübernahme. Die
Experimente betreffen simuliertes und reales autonomes Fahren. **Übertragbar
ist der Interaktionsablauf**, kein fertiges Verfahren für kooperative Montage.

„DAgger-light“ bezeichnet hier eine an DAgger angelehnte Programmverbesserung:
Code, Parameter und Erfahrungsgedächtnis ändern sich zunächst ohne Netztraining.
Die theoretischen Garantien von DAgger gelten dafür nicht automatisch.

| Rückmeldung | Lernsignal | Mögliche Änderung |
|---|---|---|
| „Diesen Karton zuerst drehen“ | neue oder korrigierte Aufgabenregel | Reihenfolge und Bedingungen |
| „Das geht unnötig umständlich“ | Bewertung mit noch unklarer Ursache | Alternativen vergleichen; keine Expertenaktion daraus erfinden |
| Teleopübernahme | Zustände und manuelle Aktionen im korrigierten Abschnitt | Referenzbewegung, Interaktionspose oder neuer Skill |
| Automatischer Prüfer meldet Strichlücke | messbarer Ergebnisfehler | Kontaktphase/Parameter untersuchen |

Eine korrigierte Episode ist nicht vollständig expertengelabelt. Vorherige
Agentenaktionen, manuelle Aktionen und spätere autonome Fortsetzung getrennt
markieren. Ein Eingriff beweist auch nicht, welcher einzelne Parameter zuvor
ursächlich war. Korrekturwissen braucht deshalb Kontext und Belege.

## Langfristiges Lernen aus jeder Ausführung

Das soll mehr umfassen als das Speichern erfolgreicher Programme. Auch ohne
erneutes Nutzerfeedback kann jede Episode neue Messungen liefern, aus denen
der Agent Verbesserungen vorschlägt und experimentell prüft.

| Dauerhafter Speicher | Inhalt | Nutzen |
|---|---|---|
| Episoden | Ausgangsszene, Codeversion, Beobachtungen/Aktionen, Kontakte, Eingriffe, Ergebnis und Fehler | vergleichbare Situationen und wiederkehrende Probleme finden |
| Regeln | Nutzeranforderungen und geprüfte Erkenntnisse mit Quelle/Geltungsbereich | Reihenfolge, Rollen, Randbedingungen wiederverwenden |
| Skillbibliothek | ausführbarer Code, Parameter, Voraussetzungen, Tests und Abhängigkeiten | weniger Neuprogrammierung bei Folgeaufträgen |
| Parameter- und Ergebniswissen | Qualität, Dauer, Erfolg/Fehler pro Kontext/Parametersatz | begrenzte Anpassung und Optimierung |

Vorbild für Lernen ohne Gewichtsupdate ist
[Reflexion, Shinn et al., NeurIPS2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html):
Ausführungsfeedback wird in sprachliche Reflexionen und episodisches Gedächtnis
überführt. Bei uns bleibt eine selbst formulierte Erklärung zunächst eine
Hypothese, die Messbezug und Prüfung benötigt.

[Voyager, Wang et al.,2023](https://voyager.minedojo.org/) kombiniert eine
wachsende Bibliothek ausführbarer Skills mit Umweltfeedback und iterativer
Codeverbesserung. Das ist ein gutes Vorbild für prozedurales Gedächtnis;
die Ergebnisse stammen aus Minecraft und belegen keine industrielle
Manipulationsfähigkeit. DROC aus dem vorherigen Review ergänzt die dauerhafte
Nutzung menschlicher Korrekturen, ACE-CaP den robotischen Entwicklungsablauf.

Beispiel: Wiederholte Zeichenläufe zeigen erhöhten Fehler auf einer bestimmten
Seite. Agent schlägt eine andere Halteorientierung oder Ansetzbewegung vor.
Beides wird zunächst einzeln auf vergleichbaren Szenen getestet. Bessere
Messwerte können einen neuen kontextbezogenen Default begründen. Der Agent
lernt dabei aus seiner Durchführung; es ist kein vollständiges Policytraining
nötig. Eine Suche über wenige kontinuierliche Parameter kann später numerisch
erfolgen; Suchverfahren und Parameterraum sind noch nicht festgelegt.

## Ergebnisprüfung ist die Voraussetzung für eigenes Lernen

Ein Programmabbruch ist ein klarer Fehler. Ein störungsfreier Ablauf ist
dagegen noch kein korrektes Arbeitsergebnis. Der Codegenerator soll nicht
seine eigene Erfolgserklärung als einziges Lernlabel verwenden. Aufgabenprüfer
werden getrennt vom jeweils veränderten Arbeitsprogramm definiert.

- **Stapelaufgabe:** Teil2 an gewünschter Position/Orientierung, tatsächlich
  unterstützt und vom Arbeitsgreifer frei; Teil1 und Haltegruppe stabil auch
  unter Zusatzlast. Ein Körper an der Sollpose allein beweist keine Stapelung.
- **Kreisaufgabe:** geforderte Seiten bearbeitet, keine unbeabsichtigte
  Doppelbearbeitung; Kreisposition/-radius/-schluss, Ebenenlage, Kontaktverlauf
  und Teilbewegung bewerten. Eine kreisförmige TCP-Bahn belegt noch keinen
  gezeichneten Kreis. Reales Strichbild benötigt eine passende Messung.

Die konkreten Maße und Toleranzen sind Aufgabenparameter, nicht aus dem
Beispielsatz zu erraten. Simulationszustände dürfen als Evaluationslabels
dienen, müssen aber als solche erkennbar sein. Reale Wahrnehmung/Kontaktregelung
darf nicht still von nur im Simulator verfügbaren Informationen abhängen.

Erfolgsrate, Qualitätsabweichung, Ausschuss, Eingriffsaufwand und Zykluszeit
gemeinsam verfolgen. Bei Zielkonflikten Prioritäten vorgeben. Eine schnellere
Variante mit schlechterem Ergebnis gilt nicht automatisch als Verbesserung.
Material, Werkzeug, Kalibrierung, Basenlage und Objektfamilie gehören zum
Geltungsbereich. Ein zufällig erfolgreicher Lauf begründet keine allgemeine Regel.

Für Industrie/Bau bietet sich folgende Trennung an: Wiederholbetrieb nutzt
einen dokumentierten Programmstand und protokolliert Erfahrungen. Dazwischen
entwickelt der Agent neue Kandidaten und prüft sie gegen diesen Stand auf
gleichen Szenen, Wiederholungen und zurückgehaltenen Varianten. Verbesserungen
erhalten neue Versionen; bekannte erfolgreiche Aufgaben bleiben als
Regressionen erhalten. Das verhindert, dass eine neue Korrektur frühere
Fähigkeiten unbemerkt verschlechtert. Lernen muss nicht jede laufende
Ausführung durch neue Codegenerierung verlangsamen.

## Konkreter Pilotvorschlag

Empfehlung, noch keine vom Nutzer ausgewählte Reihenfolge: Mit **Box halten
und Kreis zeichnen** beginnen. Das verbindet Rollen, Wiederholung,
Umorientierung und Kontakt, während sich ein geometrisches Ergebnis gut
definieren lässt. Benötigte neue Werkzeug-/Markierungs- und Prüffunktionen
sind noch nicht vorhanden oder hier nachgewiesen.

Eine ausdrücklich kleinere erste Stufe kann zwei benannte zugängliche Flächen
bearbeiten. Das erfüllt nicht bereits „jede Seite“. Für alle geforderten
Seiten müssen verdeckte Greif-/Stützflächen berücksichtigt werden; eventuell
ist eine neue Greifstrategie nötig. Nicht erreichbare Seiten explizit melden.

Der Ablauf wäre: Haltegruppe bilden, Fläche präsentieren, Ruhe bestätigen,
Werkzeug ansetzen, Kreis relativ zum Flächenframe ausführen, zurückziehen,
Kontaktende bestätigen, nächste Fläche präsentieren. Danach Stapeln als
zweite Aufgabenfamilie mit Zusatzobjekt und Lastübernahme ergänzen.

Die nächsten Entwicklungsbausteine sind:

1. Mehrrollen-Aufgabenprogramm mit messbaren Übergängen und Ereignisprotokoll.
2. Simulationsprüfer und Episodenformat; zuerst Baseline ohne Lernen.
3. Vorführung mit Sprachmarkern, Pause und lokaler Teleopübernahme.
4. Versionsgebundene Code-/Parameterkorrektur samt Regressionen.
5. Erfahrungsabruf und Verbesserung aus automatischen Ergebnissen.

Ein vorhandener Kartonviewer oder die Existenz einzelner Planer ersetzt
diese Integration nicht. Der Pilot ist zunächst Simulation; keine neue
Real-, Teleop- oder Trainingsausführung wurde in dieser Konzeptarbeit gestartet.

## Wie wir Nutzen und langfristiges Lernen nachweisen

Zunächst bei gleichem Modell/Bibliothek vergleichen: Sprache allein;
Simvorführung plus sprachliche Korrekturen; zusätzlich Teleopkorrekturen.
Danach Erfahrungsgedächtnis und automatische Ergebnisverbesserung jeweils
getrennt einschalten. Ein festes Programm ist die Ausführungsreferenz;
kleines gegen stärkeres LLM ist ein anschließender eigener Vergleich.

Messen: Gesamtzeit bis zum ersten validierten Aufgabenprogramm einschließlich
Feedback, Token-/Toolaufwand, Eingriffe und ihre Dauer, Wiederholfehler,
Arbeitsergebnis und Zykluszeit. Über viele Episoden prüfen, ob Eingriffe und
Entwicklungsaufwand sinken und Qualität erhalten bleibt. Bekannte Werkstücke
von unbekannten Varianten unterscheiden. Feste Testszenen dürfen nicht in
Erfahrungsabruf oder Parameterwahl zurückfließen; Lern- und Testphasen trennen.

Die offene Forschungsfrage ist die robuste Verbesserung kooperativer
Code-Policies aus sparsamen Korrekturen und eigener Ausführung. Sie umfasst
Ergebnisbeobachtung, richtige Verallgemeinerung und Wissenspflege. Dass die
vorgeschlagene Kombination bei unseren Aufgaben mit einem einfachen LLM gut
funktioniert, ist noch experimentell zu zeigen.
