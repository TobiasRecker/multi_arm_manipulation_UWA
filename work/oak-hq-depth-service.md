# Statischer HQ-Tiefenmodus für OAK4

- Status: **abgeschlossen**,2026-11-12, Hauptagent OAK-Tiefe.
- Auftrag: zum wiederverwendbaren HQ-Fotomodus ähnlichen Tiefenmodus umsetzen.
- Bereiche: OAK tools/oak4_depth*, Erweiterung oak4_photo_service.py/.sh,
  Tests/Anleitung und Agentenhinweise/Übergaben beider Repos/Workspace.
- Verfahren: native1280×800-Stereo, 16 verschiedene Frames, zeitlicher Median,
  Gültigkeits-/Stabilitätsmasken, keine Lochfüllung, Rohframes/Metadaten erhalten.
  ISO100 des RGB-Sensors nicht ungeprüft auf Mono-Stereo übertragen.
- Dienstneustart: nur uwa-oak4-photo.service, erst nach Statusprüfung idle.
  Gemeinsame Foto-/Tiefensperre erhalten, keine anderen Kameradienste stoppen.
- Parallel: shared-view-hardware-captures aktiv; keine Roboterbefehle.
- Prüfung: synthetische Fusion (Nullpixel/Ausreißer/Kanten/Instabilität), echte
  Serviceaufnahme/Status/Parallelzugriff und Standard-HQ-Vergleich.


Finaler regulärer HQ-Service ebenfalls real PASS:
`setup/oak4/depth/20261112-145220-depth_hq-29c6117c/`.
Status während Aufnahme CAPTURING erreichbar; paralleles RGB-Foto abgewiesen,
danach READY. **14 automatisierte Tests bestanden**. Eigener gemeinsamer Dienst
bleibt aktiv; Kamera nach dem Auftrag freigegeben.
