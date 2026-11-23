Finde im beigefügten Foto den offenen Avocado-Versandkarton aus Wellpappe.
Er hat weisse bedruckte Aussenwände, Avocado-Motive, beige Innenflächen
und teilweise gelbe Laschen am Rand. Ignoriere Roboter und Markertafeln.

Antworte ausschliesslich mit einem JSON-Objekt. Keine Werkzeuge oder Dateien
verwenden. Alle Koordinaten beziehen sich auf das angehängte Bild, Ursprung
oben links. Boxformat `[y_min, x_min, y_max, x_max]`. Positionen als ganze
Zahlen von 0 bis 1000 relativ zur jeweiligen Bildseite.

- `status`: `found`, `absent` oder `uncertain`.
- `box_2d`: Engstes Rechteck um den ganzen sichtbaren Karton einschliesslich
  Rand und Laschen. Bei `absent` oder `uncertain` muss es `null` sein.
- `front_box_2d`: Engstes Rechteck um die grosse bedruckte Vorderwand.
  `null`, wenn diese Wand verdeckt, nicht eindeutig oder kein Karton da ist.
- `front_quad_2d`: Optional vier sichtbare Ecken derselben Vorderwand in
  dieser Reihenfolge: oben links, oben rechts, unten rechts, unten links.
  Jeder Punkt ist `[y, x]` in der Originalansicht von 0 bis 1000. Nimm die
  obere Wandkante und den unteren Rand der Vorderwand am Tisch. Gelbe
  Laschen, die Seitenwände und den Innenboden auslassen. Bei verdeckten
  oder unsicheren Ecken `null` angeben.

Du kannst auch einen ersten Fit oder weitere Messergebnisse mit einem
türkisen Modelloverlay erhalten. Gib nach einem verworfenen Fit eine
korrigierte Bildregion oder ein besseres Viereck zurück. Wenn die nötigen
Merkmale nicht sicher sichtbar sind, antworte mit `uncertain`. Die
Koordinaten beziehen sich immer auf den gleichen Bildausschnitt wie beim
ersten Foto. Sende ausschließlich die Bildkoordinaten und den Status.

Beispiel für ein Bild ohne Zielobjekt:
`{"status":"absent","box_2d":null,"front_box_2d":null}`
