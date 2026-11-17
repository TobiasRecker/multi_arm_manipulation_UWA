# Vier URs zu den Seitenmitten

- Status: abgeschlossen, 2026-11-17. Nur Offlineplanung/Modellvorschau.
- Nutzer übernimmt Glättung als Standard für weitere Anfahrbeispiele.
- Neue feste Ziele an den vier Seitenmitten, eindeutig nach Nähe zugeordnet.
  Gemeinsam unter den zwei nächstgelegenen Optionen zuordnen, minimale
  Summe horizontaler Basis-Zielabstände. Greedy-Erstversuch unter primitive/
  erhalten: verdrängte LF auf Rang3, 0 LF-IK-Lösungen; keine ausführbare Bahn.
- Weiterhin von oben, 15 mm Eintauchtiefe/120 mm Voranflug, offene Greifer;
  aufrechter Start wie zuletzt. Keine Kontakt-/Hardwareaktion.
- Vorherige Eckfälle und parallele Arbeiten bleiben erhalten. Geänderte
  Geometrie und individuelle Zeiten benötigen neue vollständige Modellprüfung.
- Ergebnis: alle vier Ziele in12,746s, v/a/Ruck-Obergrenzen0,450/0,400/1,105.
  LF/RR erste Wahl, LR/RF zweite. Min.Armhüllabstand53,697mm;31 gezielteTests,
  20 Browserfälle,800.008 unabhängige Ableitungspunkte und2.551 gemeinsame
  Geometrieprüfstellungen bestanden. Standardpipeline vollständig geprüft.
- Zielauswahl mit dynamischer Reserve zunächst negativ (`case02/`), dann
  explizite Offline-Geometrieauswahl (alle6Paare/20mm/FCL); Reserve weiterhin
  sichtbar1.145/1.276 verletzt. Kein Hardware-/Kontakt-/Stoppeignungsnachweis.
- Daten: setup/research/offline-carton-sides-20261117/standard/.
  Anleitung: [offline_carton_sides.md](../docs/offline_carton_sides.md).
