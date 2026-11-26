# OAK 4 D · Klemmhalter und mobiles ChArUco rechts

[CAD-Baugruppe](cad/oak4d-tischklemme.step) · [Schnittansicht](schnittansicht.png) ·
[CAD-Prüfbericht](cad/cad-pruefung.json) · [Herstellerabgleich](cad/hersteller-abgleich.json)

## Tischklemme

Die Auflage sitzt auf der 35 mm starken Holzplatte. Eine kleine Nase
liegt außen an der Tischkante an. Zwei M8-Zugschrauben im 110-mm-Abstand
verlaufen außerhalb der Platte. Sie ziehen die Unterbacke mit einer
Stahl-Gegenplatte an das 32-mm-Profil. Die Profil-Außenfläche liegt bei
35 mm, seine Mitte bei 51 mm Abstand zur Tischkante. Holz und
Stahlprofil bleiben ungebohrt. Die Profilunterseite muss an der
gewählten Stelle frei zugänglich sein.

Die Rohrachse sitzt 30 mm innerhalb der Tischkante. Das Rohr Ø19 mm
steht auf einem Anschlag und hat 141 mm Einstecktiefe. Zwei M5-Schrauben
schließen den Schlitz in den Klemmbereichen. Der Vorentwurf der
Druckbohrung hat Ø19,4 mm. Das 145 mm hohe Oberteil trägt den Mast
und die untere Boardaufnahme. Die Längsposition wird beim Einbau
gewählt. Für die Sichtprobe lag die Achse rund 37 mm hinter der
Tischmitte, in der Nähe der heutigen OAK4.

1. [Passprobe](cad/passprobe_tisch.stl) auf der flachen Seite drucken.
   Flächen am Tisch und außen am Profil anlegen. Die Passprobe ist
   eine Querschnittslehre. Freiraum für Unterbacke und Steckschlüssel
   zusätzlich über die vollen 144 mm Klemmenbreite kontrollieren.
2. Unterbacke mit Stahl-Gegenplatte von unten ansetzen. Die Oberseite
   der Stahl-Gegenplatte greift unter die Unterseite des Stahlprofils.
   Beide M8-Verbindungen gleichmäßig anlegen. Breite Scheiben liegen
   außen an den Druckteilen auf. Eine dünne Schutzlage unter der
   oberen Auflage kann bei Bedarf ergänzt werden.
3. Das Rohr zunächst ohne Kamera einspannen. Holzauflage, Sitz der
   Gegenplatte, Klemmschlitz und Verdrehen prüfen. Das Design ist
   ein CAD-Prototyp. Reale Klemmkraft, Schwingung und Kriechen müssen
   am Aufbau beurteilt werden. Für die Kamera eine unabhängige kurze
   Fangsicherung am Stahlrahmen vorsehen.

## Boardführung

Das mobile Board **450 × 360 × 3 mm**, ChArUco PRO v1 mit IDs 100–130,
steht quer. Seine bedruckte Seite zeigt nach innen zur Zelle. Die
Rückseite liegt 31 mm weiter innen als die Rohrachse. Zwei untere
Auflagen im 110-mm-Abstand tragen es 20 mm oberhalb der Tischplatte.
Zwei rückseitige Kontaktflächen unten und eine obere Kontaktfläche
an der Schelle bestimmen seine Ebene. Dünne nachgiebige Streifen
auf der Vorderseite der unteren Führung und der oberen Lippe drücken
das Board auf diese Flächen. Streifen nach realer Plattendicke
wählen und im weißen Rand halten.

Die zweiteilige obere Schelle lässt sich seitlich am Rohr anbringen.
Ihre Höhe und Drehstellung werden einmal am eingelegten Board gewählt.
Zum Entnehmen beide M4-Knöpfe am **Schieber** lösen, den Schieber 28 mm
anheben, das Board mindestens 17 mm anheben und zur Tischinnenseite
herausnehmen. Die Schelle bleibt am Rohr. Zum Einsetzen umkehren.
Seitlichen Anschlag separat montieren. Vor Verwendung als Referenz
die wiederholte Sitzpose mit der vorgesehenen dritten Kamera messen.

## OAK 4 D und Sichtprobe

Die Kamera sitzt auf einer eigenen Neigeträgerplatte an den beiden
rückseitigen M4-Punkten mit 75 mm Abstand. Das aktuelle Hersteller-STEP
bestätigt diese Punkte. Unter der erhöhten Querbrücke ist Platz für
einen näherungsweise Ø22 × 52 mm großen geraden M12-Stecker vorgesehen.
Den tatsächlichen Stecker samt Biegeradius, ggf. M8-Kappe und
Zugentlastung vor dem Einbau abgleichen. Gewindetiefe am Gerät prüfen.
[Luxonis OAK 4 D mit Zeichnung und CAD](https://checkout.luxonis.com/products/oak-4-d)

Der Neigekopf hat eine M8-Reibachse und einen eigenen M5-Rohrklemmring.
Ausgangsmodell mit **1.270 mm Rohr** und **60° Neigung** ergibt eine
optische Höhe von ca. **2,10 m**. Die Projektion der beiden bestehenden
festen ChArUco-Muster bleibt in der idealen 4000 × 3000-Ansicht innerhalb
des Bildes. Das ist eine Sichtfeldrechnung ohne Verdeckungen. Vor dem
Ablängen den gewünschten Arbeitsbereich vergleichen. Die OAK4 muss
nach einem realen Umbau neu registriert werden.

## Teile und Schrauben

| Baugruppe | Druckdateien | Metallteile |
|---|---|---|
| Tischklemme | [Oberteil](cad/oberteil.stl), [Unterbacke](cad/unterbacke.stl) | 2 × M8-Gewindestange ca. 140 mm plus Muttern und breite Scheiben, Stahl-Gegenplatte 134 × 30 × 5 mm, 2 × M5 × 45 mm plus Muttern/Scheiben |
| Oberer Boardhalter | [Innere Schelle](cad/board_schelle_innen.stl), [äußere Schelle](cad/board_schelle_aussen.stl), [Schieber](cad/board_schieber.stl) | 2 × M5 × 35 mm plus Muttern/Scheiben, 2 × M4 × 16 mm mit Knopf und flacher M4-Mutter in der von oben zugänglichen Tasche |
| Kamerakopf | [Rohrschuh](cad/kamerakopf_rohr.stl), [Neigeträger](cad/kamerakopf_traeger.stl) | M5 × 45 mm, M8 × 50 mm mit Scheiben und Sicherungsmuttern, 2 × M4 für die Kamera, Länge nach Gerätegewinde und Auflage |

Schraubenlängen sind Startwerte aus dem CAD und mit realen Scheiben
abzugleichen. Die STLs sind in mm und auf Z = 0 gelegt. Oberteil
aufrecht drucken, an der Außenkantennase und an den Klemmlaschen
lokal stützen. Den Rohrschuh an Bohrungsanschlag und Ohren prüfen.
PETG für den Pass- und Montageprototyp ist ein Startmaterial. Das
Material für die endgültige Kameraaufnahme nach Temperatur- und
Klemmprüfung am Standort wählen.

Parametrischer CAD-Generator aus `~/UWA_ws`:

```bash
.venvs/oak-model/bin/python src/multi_arm_manipulation_UWA/hardware/oak_4d_right/make_mount.py
```

Das STEP enthält die Druckteile, Gegenplatte, Zugschrauben, Rohr,
Brett, Tischquerschnitt und das Kameragehäuse als Hüllkörper. Der
Herstellerabgleich prüft zusätzlich den echten rückseitigen
Gehäusekörper. Der Bericht enthält die abgetastete Boardentnahme und
die Freiraumprüfung des Neigekopfs von 25° bis 65° in 1°-Schritten.
