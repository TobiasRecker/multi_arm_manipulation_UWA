# Hydrogen-Nachmessung für den Kartongriff

Status: abgeschlossen, 23.11.2026 AWST. Nutzerauftrag zur Rückkopplung
nach der Hydrogen-Kartonerkennung. Der Dialog sendet nach einem verworfenen
Fit Messwerte und Modelloverlay, soweit vorhanden. Hydrogen kann in
derselben Sitzung ein neues Fenster oder ein Viereck der bedruckten
Vorderwand wählen. Bis zu drei geführte Messungen. OpenCV sucht Merkmale
in der entzerrten Wand und bindet sie für Projektion und Tischauflage
an die nativen Pixel zurück.

Offline-Nachlauf am zuvor verworfenen Foto aus
`cd940bec4d5d4f16a58a92a3b1df3069`. Der Standardfit ergab null
akzeptierte Hypothesen. Hydrogen erhielt diesen Befund und das Overlay.
Die nächste Messung lieferte zwei gültige Hypothesen bei einer
Grenze von 6,375 px RMS. Aus der angepassten Bildregion 5,936 px bei
56 Inliers, aus der entzerrten Vorderwand 5,511 px bei 69 Inliers.
Die Lagen stimmen bis auf 2,535 mm und 0,559° überein. Die bestehende
Bahnplanung berechnete aus dem archivierten Gelenkzustand parallele
Hochanfahrt (40,962 s) und offene Einfahrt (7,946 s) für beide rechten Arme.
Der Ablauf mit einem abgelehnten geführten Fit und der anschließenden
Nachmessung in derselben Sitzung wurde als Offline-Regression geprüft.
Insgesamt 19 Tests bestanden.

Der N100 besitzt die SHA-gleiche Registrierungsdatei, mit Rücksicherung
in `~/uwa-ur-runtime/review-candidates/carton-hydrogen-feedback.0oN3Oi2p`.
Die Program Library lädt den ROSmini-Worker beim nächsten Start.
Ein neuer realer Greiflauf steht aus.

[Hydrogen-Dialog](../../../setup/tasks/carton-hydrogen-feedback-20261123/replay/hydrogen.json) ·
[Fitbericht](../../../setup/tasks/carton-hydrogen-feedback-20261123/replay/registration-hydrogen/registration.json) ·
[Bahnprüfung](../../../setup/tasks/carton-hydrogen-feedback-20261123/offline-plan/workflow.json)
