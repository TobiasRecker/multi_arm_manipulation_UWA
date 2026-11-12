# Vorläufige OAK-Pose übernehmen

- Status: **abgeschlossen**, 2026-11-12, Hauptagent.
- Nutzer akzeptiert die erklärte erste Drei-Kamera-Schätzung für erste Versuche
  und beauftragt die Übernahme in digitale Zelle, RViz und Gazebo.
- Separates versioniertes Folgeprofil mit SHA256-gebundener Nutzerübernahme;
  Qualitätsflags/Originalergebnis erhalten. Relative Optikpose über gemessene
  Front-Gelenkstellung, Werkskinematik und übernommene Hand-Auge-Matrix zur
  vorläufigen Zellpose umrechnen. Welt-/Tischanker bleiben unvermessen.
- Zentrale Loader/Overview-Consumer/Tests/Dokumentation; keine Armbewegung,
  keine Hardwaretreiberneustarts. Laufende LinksFront-Aufgabe erhalten.
- Vor GUI-/Gazebo-Aktualisierung Dienste prüfen; nur Kamera neu laden, keine
  laufenden Roboter-/Simulationszustände zurücksetzen.
- Standardprofil auf hardware_20261112_v3 umgestellt. Roboter-/Tischgeometrie,
  Initialgelenke und bisherige Roboterfits bytegleich; Profilfingerprint ändert
  sich dennoch. Andere Aufgaben müssen alte Planartefakte regulär neu prüfen,
  keine gespeicherten Fingerprints umschreiben. Keine Hardwaredienste angefasst.
- Aktiv: hardware_20261112_v3,Pose[1,2203;0,0522;1,8578]m,raumfest und
  explizitvorläufig. PhysischeRational14 erhalten; Ogre2rendertOAKPinhole/D0.
  NurSim-OAK-HelferfürMetadatenneugeladen, keineZelle/Armezurückgesetzt.
- 3Paketegebaut,40TestsPASS, LiveGazebo/RVizTF/K/D/ScenePose/9ControllerPASS.
  DigitaleZelle/Gazebo/RViz/Scanlaufen,keineHardwarekommandos.
  Nachweise adoption-live/ und uwa-oak-profile-adoption-*Logs. HANDOVER,
  AGENTS,README unddocs/oak_preliminary_adoption_2026-11-12.md aktualisiert.
