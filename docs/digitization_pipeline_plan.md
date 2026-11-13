# Schnellere Objektdigitalisierung mit geringem Reasoning-Aufwand

Stand 13.11.2026: **Umsetzungsvorschlag**, noch keine neue ausführbare Pipeline.
Nutzer möchte kürzere Durchlaufzeiten mit möglichst gleicher Qualität und
Sicherheit; geringerer Reasoning-Aufwand ist erwünscht, aber noch nicht umgestellt.

## Befund aus den bisherigen Objekten

Die vorhandenen Aufnahmen, Optikmodelle, Optimierer, CAD-Exporte, Assetloader und
Prüfungen sind wiederverwendbar. Der Ablauf ist dennoch assistierte Entwicklung:
`reconstruct_ptfe_l.py` enthält eine besondere Form-/Eckdefinition und feste
Materialstärken; `texture_ptfe_l.py` noch manuell bestimmte Bildkoordinaten.
`reconstruct_carton_scan.prepare` kennt konkrete lokale Optikquellen. Es gibt
noch keinen generischen, getesteten Auftrag von Aufnahme bis fertigem Asset.

Das erfolgreiche PTFE-Fünferset dauerte laut Manifest **44,34 s** vom Start bis
zum Ende des Sets. Fokusvorbereitung/-wiederherstellung, der vorangegangene
Fehlversuch, Geometriearbeit, Export und Agentenzeit sind darin nicht enthalten.
Eine vollständige Zeitaufschlüsselung fehlt. Große Einsparungen werden zunächst
bei Entwicklung, Diagnose und wiederholtem Kontextaufbau erwartet; ein Faktor
oder eine Gesamtzeit kann daraus noch nicht zugesichert werden.

Wiederholung bringt nur dann dauerhaften Gewinn, wenn neue Erkenntnisse in
getestete Funktionen, Formvorlagen und kleine Arbeitsanweisungen überführt
werden. Mehr Chatverlauf allein ersetzt diese Arbeit nicht.

## Zielaufteilung

| Zuständigkeit | Aufgabe |
|---|---|
| Geprüfte Programme | Daten prüfen, Kamera-/Aufnahmeablauf, rechnen, exportieren, Grenzen prüfen, Berichte schreiben |
| Schneller Agent mit wenig Reasoning | Objektauftrag ausfüllen, vorhandene Formvorlage wählen, Prüfprogramme aufrufen, Ergebnisse verständlich zeigen |
| Gezielte fachliche Bearbeitung | unbekannte Form, widersprüchliche Ansichten, uneindeutige Ecken/Masken, ungültige Kalibrierung, neuer Algorithmus |

Der schnelle Durchlauf schreibt keinen neuen Python-Code und verändert weder
Prüfgrenzen noch Kalibrierungen. Unsichere Bildzuordnungen werden als solche
ausgegeben; ein Agentensicherheitswert ersetzt keine geometrische Prüfung.
Begrenzte strukturierte Bildanalyse ist möglich, benötigt aber dieselben Tests
und kann auch bei wenig Reasoning scheitern.

Eine kurze repo-lokale Skill soll Aufrufe, Eingaben, Fehlercodes und Beispiele
erklären. Das entspricht dem Zweck von [Skills](https://developers.openai.com/plugins/concepts/skills).
Die eigentliche Durchsetzung liegt im Runner und seinen Schnittstellen, nicht
in der bloßen Aufforderung an das Modell, vorsichtig zu sein. Zunächst keinen
neuen Modellanbieter, keine eigene API-Anbindung und keinen zusätzlichen Agenten
für jede Stufe voraussetzen. Verfügbare Reasoning-Stufen hängen von Modell und
Client ab: [Codex-Konfiguration](https://learn.chatgpt.com/docs/config-file/config-reference).

## Festgelegter Ablauf pro Objekt

1. **Auftrag und Voraussetzungen:** eigene Objekt-ID, gewünschtes Ergebnis
   (Darstellung/CAD/Tracking), Formvorlage und bekannte Maße samt Herkunft.
   Kameraprofile, Auflösung/Fokus, Nutzungssperren und erforderliche Telemetrie
   prüfen. Erste Version nur mit vorhandenen ruhenden Kamerastellungen.
2. **Einmal aufnehmen:** bestehender Fünfkamera-Capture mit unabhängiger
   Stillstandsprüfung, Originalbildern und bestätigter Wiederherstellung.
   Bei Wiederaufnahme keine bereits abgeschlossene Aufnahme still wiederholen.
3. **Daten vorbereiten:** passende K/D einfrieren, Board-/Bildqualität prüfen,
   Objektbereich und beobachtete Flächen erfassen. Rohkoordinaten und
   Vorschautransformationen explizit speichern. Prüfaufnahmen vor dem Fit
   festlegen; Quellen- und Prüfzugehörigkeit je Stufe führen.
4. **Form fitten:** gemeinsame Schnittstelle für zunächst Kasten/Schale und
   rechtwinklige Plattenkonstruktion, statt weiterer Skripte je Objekt. Material-
   stärken und Merkmalszuordnungen sind Daten. Bei Bedarf wenige klar benannte
   Ecken/Flächen korrigieren, statt vom Agenten ganzen Code neu erstellen lassen.
   Unbekannte Form führt zu einer begrenzten Fachfrage, nicht zur erzwungenen
   Kasten- oder L-Näherung. Freiformmesh ist eine spätere eigene Erweiterung.
5. **Automatisch prüfen und texturieren:** unabhängige Reprojektion, Sichtbarkeit,
   Skalierung, Plausibilität und bekannte Kontrollmaße; dann Flächentexturen
   nach definierten Zuordnungen erzeugen. Spiegelungen, Verdeckungen und
   ungemessene Rückseiten explizit behandeln. Grenzwerte vor Vergleichsläufen
   pro Formfamilie versionieren; nicht passend zum aktuellen Resultat lockern.
6. **Export und Bericht:** STEP/STL/GLB/DAE, Einheiten-/Hash-/Geometrieprüfungen,
   automatisch erzeugte Ansichten und kompakte Zusammenfassung. Bestehende
   Assets behalten; neue Version zunächst als Kandidat. Tracking separat auf
   Bildern prüfen, die nicht seine Textur-/Referenzquelle waren.

Darstellung, geometrische Genauigkeit, Wiedererkennung und Eignung für Physik/
Manipulation erhalten **getrennte Qualitätszustände**. Beim heutigen PTFE-Modell
bleiben insbesondere Restfehler und Tracking-LOST sichtbar. Ein hübsches oder
geschlossenes Modell gilt deshalb nicht automatisch als maßhaltig oder trackbar.
Assetfreigabe ist keine Freigabe einer Roboterbewegung oder Manipulation.

## Runner, Wiederaufnahme und kleine Agentenschnittstelle

Ein Auftrag besitzt versionierte `job.json`, Eingaben, Ergebnisse pro Stufe,
Prüfbericht und Status. Vorgesehene Zustände: RUNNING, DONE, NEEDS_INPUT, FAILED,
CANCELLED; Wartegrund, nächster erlaubter Schritt und belegte Ergebnisdateien
werden maschinenlesbar ausgegeben. Das sind geplante Schnittstellen, noch keine
heute verfügbaren neuen CLI-Befehle.

Der Agent erhält eine kompakte Zusammenfassung und erforderliche Vorschaubilder;
Details nur bei einer konkreten Abweichung. Fachliche Leitdokumente bleiben
verbindlich, aber historische Sitzungslogs werden nicht fortlaufend mitgeladen.
Abgeschlossene Berechnungen können mit einem Schlüssel aus Bild-, Optik-,
Annotations-, Formmodell-, Prüfregel-, Code- und Umgebungsstand wiederverwendet
werden. Änderungen invalidieren die betroffene Stufe und ihre Nachfolger.
Eine neue reale Szene braucht neue Bilder; alte Bilder werden nicht zu Live-Daten.

Technische Wiederholungen begrenzen; keine endlosen Optimierungs-/Reparatur-
schleifen. Daten-/Geometriewidersprüche liefern einen kleinen Diagnoseauftrag
mit Bildern, Residuen und konkreter Frage. Höheren Reasoning-Aufwand gezielt
dort einsetzen. Keine pauschale Eskalation für jeden normalen Arbeitsschritt.
Nebenläufige Kamera-/Rechenarbeit nur bei tatsächlich unabhängigen Ressourcen;
OAK-Fotolease und laufende fremde Arbeiten erhalten.

## Sicherheit bei geringerem Reasoning-Aufwand

Bestehende Kamera-/Telemetrie-/Kollisions-/Stoppfunktionen bleiben in Software
außerhalb der Modellentscheidung. Fehlende/veraltete Zustände stoppen den
betroffenen Ablauf; niemals zum Erfolg umdeuten. Die erste schnelle Pipeline
enthält keine Armfahrt. Eine spätere optionale Ansichtsplanung braucht eigene
vorab geprüfte Wege und den vorhandenen unabhängigen Bewegungswächter.
Ein kleiner Versatz oder vermeintlich einfache Form ist kein Kollisionsnachweis.

Geräteänderungen und Stillstands-/Stoppreaktionen hängen nicht davon ab, wann
der Agent antwortet. Abbruch/Prozessverlust dürfen keine neue Fahrt auslösen;
Kamera-Restore/LED-Regel bleiben erhalten. Codeprüfungen und eine erlaubte
Runner-Schnittstelle begrenzen Aktionen; ein SKILL.md allein erzwingt dies nicht.

## Umsetzung und Abnahme

1. Zuerst gemeinsame Datenschemata, konfigurierbare Formfamilien, feste
   Prüfberichte und Runner aus den vorhandenen Werkzeugen extrahieren.
2. Beide gespeicherten Objekte vollständig offline reproduzieren. Dabei
   Sicht-/Fit-/Trackingfehler erhalten, nicht die heutigen Warnungen zu PASS
   erklären. Fehlerfälle für falsche K/D, Achsen/Einheiten, vertauschte Ecken,
   veraltete Eingaben, fehlende Ansichten und Abbruch einbauen.
3. Identische Aufgaben mehrfach mit niedrigerem und bisherigem Reasoning-Aufwand
   vergleichen: Gesamtzeit, Gerätezeit, Rechenzeit, Agenten-/Werkzeugrunden,
   Korrekturbedarf, Fehlererkennung und Ergebnisqualität getrennt messen.
   Gleiche Eingaben und Prüfregeln; keine Hardware für diese Wiederholungen.
4. Danach ein neues einfaches Objekt ohne neuen objektspezifischen Code prüfen.
   Das ist der Übertragungsnachweis; erfolgreiche Wiedergabe bekannter Objekte
   allein genügt nicht. Bei unbekannten Formen muss die Ausnahme funktionieren.
5. Erst nach dieser Abnahme den schnellen Modus als Routine nutzen, später
   zusätzliche Ansichten und weitere Geometrie-/Trackingbackends ergänzen.

Angestrebter Routinefall: ein Auftrag, eine Aufnahme, wenige strukturierte
Eingaben und ein Prüfbericht statt längerer Entwicklungsarbeit. Zeitziele und
Modellwahl nach der Messung festlegen. Der sichere Gewinn entsteht aus weniger
offenen Entscheidungen und zuverlässig erkannten Grenzen.
