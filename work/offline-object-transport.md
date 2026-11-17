# Vierarm-Objekttransport mit Orientierungsoptimierung

- Status: erster Offline-Transport und Yaw-Gradientenversuch abgeschlossen,
  2026-11-17. Nutzer beauftragt den nächsten Schritt.
- Aus letzter Seitenmitten-Endstellung, hypothetisch feste Griffe bei weiterhin
  offener Greifergeometrie. Keine Kontaktphysik-/Hardware-/ROS-Knotenaktion.
- Zunächst Idealprofil anheben/20cm versetzen/absetzen, dann gradientengeführte
  Orientierungsoptimierung mit gemeinsamem Zeitgesetz. Keine Einzelarm-Retimings.
- Nutzerantwort: Richtung anhand Erreichbarkeit wählen. Welt−X besteht;
  10cm Hub,±15°Yaw, waagerechter Karton als Versuchsannahmen.
- Neue isolierte Module/Tools/Artefakte, parallele Arbeiten erhalten.
- Ideal17,532s/32,676mm; separater Zusatzabstandsversuch15,332s/max6,017°Yaw.
  Beide mit gemeinsamem24Gelenk-Zeitgesetz,≤5ms-Kollisions-/Griffzwangprüfung
  bestanden. AnalytischeGradienten mit zentralenIK-Differenzen abgeglichen;
  absichtlicheTischkollision erkannt. Frühere zu grobe Optimierung als Negativfall
  erhalten. Build,5CTest-Suiten und28Browserchecks bestanden.
- Ergebnis `setup/research/offline-object-transport-20261117/final/viewer.html`,
  Bedienung `docs/offline_object_transport.md`, Details imHANDOVER.
- Offen für folgenden Schritt: räumlicher Korridor/Translationsgradienten in der
  Optimierung, differenzierbare Umweltabstände, andereIK-Zweige/engereFälle,
  bewegteBasen. PhysischerGriff und tragfähigesAbsetzen separat; dieses Ergebnis
  verwendet weiterhin offeneGreifer und nominal3mmTischspalt.
