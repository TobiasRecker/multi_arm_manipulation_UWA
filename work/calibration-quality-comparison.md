# Qualität und Bildzahl der realen Kalibrierung

- Status: **abgeschlossen – Offline-Bewertung und Vergleichsvorschlag**,2026-11-11.
- Nutzer fragt nach Mehrwert zusätzlicher Bilder und schlägt Front-Reihe mit
 50% mehr Bildern nach Rear-Parken vor. Zunächst vorhandene Daten offline
  beurteilen und ein kontrolliertes Vergleichsdesign festhalten.
- Keine Hardwarefahrt, Treiberneustarts oder Kameraänderungen in dieser Analyse.
- Bereiche: eigener Offline-Auswertungsreport unter setup/calibration/,
  HANDOVER.md und ggf. Bedienungsdokumentation. Bestehende Profile erhalten.
- Gleicher Kameratyp ist nicht automatisch dieselbe physische Kamera oder
  identische Intrinsics/Montage. Kameraidentität nicht ungeprüft gleichsetzen.
- Bildzahlwirkung innerhalb derselben Kamera mit festen Prüfbildern vergleichen;
  Front/Rear-Vergleich zusätzlich durch Montage, Sichtwinkel und Optik beeinflusst.
- Neun Offline-Fits:4×20/4×26/1×33 Trainingsbilder gegen dieselben8 Prüfbilder.
  Intrinsics-Prüfmedian stets etwa0,22px; Hand-Auge0,40–0,50px, kein klarer
  monotoner Bildzahlvorteil. Ergebnisprofil/Rohdaten unverändert.
- Empfehlung als Vorschlag dokumentiert: ca62 Front-Ansichten mit50 Fit/12
  Prüfung, gezieltere räumliche Abdeckung, kleinere Trainings-Teilmengen gegen
  dieselben Prüfbilder vergleichen. Keine tatsächlichen Hardwarefahrten.
- Bericht/Unsicherheiten/Grenzen: docs/calibration_quality_review_2026-11-11.md;
  Auswertungsdaten unter setup/calibration/hardware_handeye/
  right_rear_20261111/quality_review/. HANDOVER/AGENTS aktualisiert.
