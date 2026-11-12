# Vorläufige OAK-Pose übernehmen

- Status: **in Arbeit**, 2026-11-12, Hauptagent.
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
