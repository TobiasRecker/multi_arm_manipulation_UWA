from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
root=Path(__file__).resolve().parents[1]
out=root/'output/pdf/uwa_offline_multiarm_plan_2026-11-17.pdf';out.parent.mkdir(parents=True,exist_ok=True)
for n,f in [('D','DejaVuSans.ttf'),('DB','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(n,'/usr/share/fonts/truetype/dejavu/'+f))
s=getSampleStyleSheet()
for n in ['Normal','BodyText','Title','Heading1','Heading2']:s[n].fontName='D'
s['BodyText'].fontSize=10;s['BodyText'].leading=15;s['BodyText'].spaceAfter=9
s['Title'].fontName='DB';s['Title'].fontSize=25;s['Title'].leading=31;s['Title'].textColor=colors.HexColor('#12334b')
s['Heading1'].fontName='DB';s['Heading1'].fontSize=18;s['Heading1'].leading=23
s['Heading2'].fontName='DB';s['Heading2'].fontSize=12;s['Heading2'].leading=17;s['Heading2'].spaceBefore=12
story=[]
def p(t,style='BodyText'):story.append(Paragraph(t,s[style]))
def h(t):p(t,'Heading2')
def page():story.append(PageBreak())
def foot(c,d):
 c.setFont('D',8);c.setFillColor(colors.HexColor('#334155'));c.drawString(42,25,'UWA | Offlineplanung | 17. November 2026');c.drawRightString(553,25,f'{d.page} / 3')
p('Kollisionsfreie Offlineplanung für vier URs','Title')
p('Umsetzungsplan und Vergleichsstrategie | Stand 17. November 2026')
h('Ziel und Umfang')
p('Aus einer Aufgabe mehrere geeignete Zielkonfigurationen erzeugen, glatte Einzelwege planen und deren zeitliche Ausführung kollisionsfrei koordinieren. Alle Arm- und Basisbewegungen gelten in der Planung als bekannt. Zwei Tische mit je zwei URs sind das erste Fallbeispiel. Reaktive Regelung und unbekannte externe Störungen gehören zunächst nicht zum Umfang.')
h('Die fünf Planungsschritte')
for title,body in [
('1  Zielkandidaten erzeugen','Mehrere erlaubte TCP-Posen und IK-Lösungen je Arm behalten. Gelenkgrenzen, Posefehler und Herkunft dokumentieren. Keine frühe Festlegung auf nur eine IK-Lösung.'),
('2  Gemeinsame Ziele auswählen','Kandidatenkombinationen gegen die vollständige modellierte Zelle prüfen. Andere ausgewählte Arme dürfen ihre Startstellung verlassen. Einzeln günstige Ziele sind nicht automatisch gemeinsam erreichbar.'),
('3  Glatte Einzelwege aufbauen','Möglichst MoveJ-/MoveL-nahe Primitive mit modellierten Übergängen nutzen. Wenige alternative Wege je Ziel behalten. Blending und Zeitgesetz gehören zur zu prüfenden Bewegung.'),
('4  Konflikte zeitlich lösen','Startzeiten, Reihenfolge und zulässige Geschwindigkeitsprofile koordinieren. Wenn Warten nicht reicht, zu einer anderen Bahn oder Zielkombination zurückspringen.'),
('5  Ergebnis vollständig prüfen','Finale interpolierte und zeitparametrierte Bewegung mit allen Körpern prüfen. Planungszeit, Fahrzeit, Abstand und Fehlschläge separat berichten. Erst später folgt Ausführungsqualifikation.')]:
 h(title);p(body)
page();p('Koordination und Vergleich','Heading1')
h('Bahnfortschritt statt vollständigem Gelenkraster')
p('Für einen festen Einzelweg beschreibt s zwischen 0 und 1 den Fortschritt. Für jedes der sechs Armpaare entsteht eine Konfliktkarte über die beiden Fortschritte. Der Koordinator sucht einen monotonen Verlauf vom gemeinsamen Start zum gemeinsamen Ziel. Warten muss mit Beschleunigungs- und Bremsbedingungen vereinbar sein.')
p('Raum-Zeit-Voxel sind eine ergänzende Reservierungs- und Vorfilterdarstellung. Ganze Link- und Werkzeugvolumina sowie Zwischenbewegungen erfassen; TCP-Zellen allein genügen nicht. Bei vorgegebenen bewegten Basen hängt eine Konfliktkarte zusätzlich von der Zeit ab.')
h('Vier vergleichbare Varianten')
for title,body in [
('Referenz: gemeinsame RRTConnect-Planung','Vorhandene gemeinsame Samplingplanung als Vergleich erhalten. Die erste Referenz nutzt feste Basen; bekannte Basisbahnen verlangen später eine Raum-Zeit-Erweiterung.'),
('Hauptansatz: Einzelwege und Konfliktauflösung','Ziel- und Wegalternativen mit priorisierter Planung, Wartezeiten und gegebenenfalls CBS-artiger Neuplanung kombinieren. Stop-N-Go und xCBS/xECBS dienen als methodische Referenzen.'),
('Moderner Vergleich: Diffusionsplanung','Gelernte Bewegungsvorschläge und paarweise Konfliktreparatur nach Diffusion-Guided Multi-Arm Planning untersuchen. Geometrische Prüfung bleibt gemeinsam.'),
('Eigene Lernvariante: Abstandsproxy','Paarweise Mindestabstände aus beiden Gelenkzuständen und relativer Basispose schätzen. Geometrisch gelabelte Daten, gezieltes Sampling nahe Kontakt und unabhängige Prüfung. Clearance in Metern ist kein Gelenkraum-CDF.')]:h(title);p(body)
h('Fair messen')
p('Gleiche Aufgaben, Geometrien, Zieloptionen und physische Abstandsvorgaben. Datenvorbereitung/Training, Online-Planung und Endprüfung getrennt messen. Erfolgsquote, Wartezeit, Gesamtdauer, Glätte und Abstand auswerten. Ungültige Ziele und unlösbare Fälle bleiben im Bericht. cuRoboV2 ist ein optionaler zusätzlicher Vergleich; lokale Eignung ist noch nicht nachgewiesen.')
page();p('Erster Umsetzungsschritt','Heading1')
h('Eingabe und Ausgabe')
p('Eingabe: vollständiger Modell-Startzustand mit Greifern, aktive Arm-IDs und je Arm eine oder mehrere explizite Welt-TCP-Posen oder Gelenkziele. Robotermodelle und Werkskinematik aus dem bestehenden Zellmodell verwenden; keine parallelen Kinematikparameter.')
p('Ausgabe: mehrere nummerierte Kandidaten je Arm mit Zielherkunft, Gelenkwerten, Posefehlern und Abstand zur Startkonfiguration. Ergänzend eine begrenzte Liste geometrisch gültiger Zielkombinationen. Modell-/Meshbindung, Suchbudget und Abbrüche dokumentieren.')
h('Abnahmekriterien der ersten Stufe')
p('Mehrere unterschiedliche IK-Lösungen können erhalten bleiben. Rückrechnung der TCP-Pose bestätigt die Zieltreue. Fehlende Zustände, falsche Frames, ungültige Quaternionen und Gelenkgrenzen werden erkannt. Unerreichbare Ziele werden explizit gemeldet. Kandidaten gelten nicht als kollisionsfrei, bevor eine vollständige Zielkombination geprüft wurde.')
p('Eine gültige Endstellung ist noch kein freier Weg. Ein ausgeschöpftes Suchbudget ist kein Beweis der Unlösbarkeit. Die erste Stufe erzeugt einen Offlinebericht, keine Fahrbefehle. Bewegte Basisbahnen und automatische Ableitung von Greifposen aus einer frei formulierten Aufgabe sind weitere Schritte.')
h('Bewegungsfunktionen als Planungsvertrag')
p('MoveJ interpoliert im Gelenkraum; MoveL führt den TCP relativ zur Basis. Die endgültige primitivebasierte Bahn einschließlich Blending prüfen. Eine beliebige Splinebahn wird durch Übergabe ihrer Endpose an MoveJ nicht reproduziert. Weltbewegung einer fahrenden Basis separat einrechnen.')
h('Ausgewählte Quellen')
for name,url in [
('Stop-N-Go: zeitliche Konfliktlösung','https://arxiv.org/abs/2410.07606'),
('xCBS/xECBS: Mehrarmplanung','https://arxiv.org/abs/2404.00143'),
('Diffusion-Guided Multi-Arm Planning, CoRL 2025','https://proceedings.mlr.press/v305/parimi25a.html'),
('DiffCo: differenzierbarer Kollisionsproxy','https://arxiv.org/abs/2102.07413'),
('cuRoboV2: Dynamik und B-Spline-Optimierung','https://arxiv.org/abs/2603.05493')]:
 p(f'<link href="{url}" color="#154c79">{name}</link>')
p('Ausführliche Quellen und Abgrenzungen: docs/mobile_multiarm_planning_survey_2026-11-16.md im Zell-Repository.')
SimpleDocTemplate(str(out),pagesize=(595.28,841.89),rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=45,title='UWA Offlineplanung für vier URs',author='UWA Projekt').build(story,onFirstPage=foot,onLaterPages=foot)
print(out)
