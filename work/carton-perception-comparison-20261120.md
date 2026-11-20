# Kantengeometrie, FoundationPose und Bildmerkmale am Karton

- Status abgeschlossen, 20.11.2026, Australia/Perth. Nutzer beauftragt den Vergleich
  eines direkten Randfits mit FoundationPose und automatischer Startmaske.
  Er möchte SIFT und ORB für diesen Karton einordnen.
- Bereiche sind die aufgezeichneten OAK4-Bilder, die archivierten RGB-D-Paare
  und die vorhandene FoundationPose-Umgebung auf titanpc. Ergebnisse unter
  `setup/tasks/carton_perception_comparison_20261120/`.
- Vergleich erfolgt offline. Laufender Kartonpilot und reale UR-Dienste
  dienen dabei nicht als Versuchsoberfläche. Keine Dienstneustarts geplant.
- Beide Pfade liefen als Archivversuch. Kanten allein sprangen um 33,1 mm
  am Mittelpunkt. Mit gelben Randlaschen als Silhouettenhinweis betrug die
  Streuung 1,24 mm. FoundationPose lieferte mit der automatisch erzeugten
  Maske acht gültige Posen. Der Start unterschied sich um 0,44 mm und
  0,13° vom gespeicherten Handmaskenlauf. Beide Merkmalsmethoden erreichten
  zwei von drei Registrierungen, SIFT lieferte mehr gültige Fits und ORB
  lief schneller. Dauerhafte Auswertung in [HANDOVER](../HANDOVER.md).
