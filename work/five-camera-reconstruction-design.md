# Vier Wrist-Kameras plus OAK für Objektrekonstruktion

- Status: **abgeschlossen – Recherche und Scan-Konzept dokumentiert**,2026-11-12,Hauptagent Digitalisierung.
- Nutzer möchte gemeinsamen Objekt-Scanbereich mit allen vier Armen+OAK,
  fünf Fotos pro Aufnahme und optional kleine zusätzliche Kamerabewegungen.
  Bestehende Bildrekonstruktionsverfahren ausLiteratur prüfen und sinnvoll
  mit dem bisherigen parametrischenCAD-Fit verbinden.
- Jetzt: Recherche/Bestandsprüfung und konkret dokumentiertes Scan-Konzept;
  keine reale Fahrt/Kameraaufnahme, keine laufenden RR-/LF-HD-Reihen berühren.
  KleineTCP-Verschiebung ersetzt keine vollständige Gelenk-/Wegkollisionsprüfung.
- GemeinsamerScanbereich muss Sicht/Erreichbarkeit allerArme erfüllen; aktuelle
  Ansichten auf jeeigenesTischboard sind nochkeinNachweis für dasselbeObjekt.
- Recherche nurPrimärquellen: COLMAP, MASt3R/DUSt3R,VGGT,Nerfstudio/OpenMVS.
  Prüfen: Metrik/Skala, Geometrie statt reinerAnsichtssynthese, vorhandeneK/D,
  wechselnde relativeArmkameraposen, CPU/GPU-Voraussetzungen.
- Bereiche: docs/five_camera_reconstruction.md,Scan-Designprofil unterconfig/,
  README/AGENTS/HANDOVER. Keine Kalibrierungen oderBewegungsprogramme ändern.

- Ergebnis: docs/five_camera_reconstruction.md mitPrimärquellen undEmpfehlung
  Geometrie/Lernverfahren→Mesh→CAD;5Initial-/13–21erweitertenPerspektiven,
  getrennteKameraintrinsics/Posen,Objektmasken/Maßstab/Prüfansichten.
- Design-YAML syntaktisch/Ansichtszählergeprüft,nichtausführbar/keinConsumer.
  GemeinsameScanposeistweiterzuprüfen,bisherigePosenschauenaufjeeigeneBoards.
- HostnurIntelGrafikerkannt;COLMAPSparseCPU,DensebenötigtCUDA. KeineModelle
  installiert/getestet,keineAusführungserfolgeoderKollisionfreiheitbehaupten.
- README/AGENTS/HANDOVERgepflegt.KeineArm-/Kamera-/Kalibriertransaktion.
