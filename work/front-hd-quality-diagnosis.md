# Front-HD-Qualität und Auflösungsvergleich

- Status: **abgeschlossen – Pixelgrenze als Intrinsics-Abbruchgrund eingegrenzt**,2026-11-12,Hauptagent.
- Auftrag: erklären, warum HD nicht bestanden hat, während Front-VGA-Intrinsics
  bestanden hatten. Frühere Front-Hand-Auge-Qualität separat prüfen.
- Nur Offline-Auswertung bestehender Originalbilder; keine Roboter-/Kamerakommandos,
  Dienstneustarts, Profilaktivierungen oder Änderungen der Freigabegrenzen.
- Bereiche: eigene Diagnose unter right_front_hd_20261112/resolution_diagnosis_v1/,
  docs/front_hd_calibration_2026-11-12.md und HANDOVER.md.
- Prüfungen: pixelnormierter Vergleich; dieselben40HD-Bilder bei640×480 erneut
  erkennen; dokumentierte ArUco-Eckenverfeinerung als mögliche Fehlerquelle
  separat untersuchen. 32/8-Rollen bleiben fix, keine Sicht ausgeschlossen.

- Nachweis: dieselben40HD-Bilder verkleinert+neu erkannt: Fit0,315px,
  Prüfmedian0,276px; reinePunktskalierung0,296/0,248px. HD1,198px ist damit
  keinBelegfürentsprechendschlechtereGeometrie. Produktionsschwelle bleibt.
- AlteFront-Hand-Augewarbereitsabgelehnt(0,652°),aktuell0,588°ebenfalls.
  Ursache verbleibenderRotationnichtisoliert. ArUco-Subpixelablationpraktisch
  ohneEffekt. In-Stream-ReadbacknativerKamerakontrollwertealsPrüflückebenannt.
- Originalhashes80/80unverändert. Dokumenteobenaktualisiert. KeineDienstneustarts,
  Hardwarekommandos,ProduktionsänderungenoderProfilaktivierungen.
