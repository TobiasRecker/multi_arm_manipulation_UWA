# Start des tischgestützten Kartongriffs

Stand 23.11.2026, in Bearbeitung. Codex untersucht den Library-Lauf
`01fdc7a4a84c4fd4b580ccd949b15c09`, den Start unter unbeladenen Holds
und die Meldungen im Browser und Safety Log. Betroffen sind der Kartonstart,
die Ausführungsdiagnose und die Bedienanleitung. Kein Dienstneustart geplant.

Um 15:12:25 AWST scheiterte die erste Hochanfahrt vor dem ersten Ziel.
Im Phasenbericht sind Arm- und Fingerbefehle leer. Alle vier letzten
nativen Geschwindigkeitsvektoren waren null. Der Browser hatte zuvor beide
rechten Programme als bereits laufend erkannt und die Hold-Vorbereitung
übersprungen. Eine spätere lesende Supervisorabfrage ergab CLEAR mit null
verriegelten und null gehaltenen Armen bei bestätigten Manager-, Hardware-
und Hold-Konfigurationsmeldungen. Der alte Phasenbericht speichert das
Supervisorpaket des Abbruchzeitpunkts nicht.

Der N100 lädt die drei geprüften Kartonmodule. Rücksicherung in
`~/uwa-ur-runtime/review-candidates/carton-holds-2311.ZjClEXj2/previous`.
28 vorhandene Softwareprüfungen bestanden. Im Offline-Nachlauf der
gespeicherten Supervisorlage wurden ausschließlich die fehlenden Holds
angefordert. Bei bereits gehaltenen Armen blieben die Anfragen aus.
Die neue Safety-Log-Erfassung ordnet den alten Abbruch dem Originalworkflow
als „Blocked before phase command“ zu.
[Messwerte und Nachlauf](../../../setup/tasks/carton-holds-20261123/)

Neuer realer Browserlauf `ab48f95c01af4ae2bbfb8123b52033c6` auf
Nutzerwunsch um 15:26 AWST angestoßen. Alle vier Holds waren beim neuen
Start bereits bestätigt, beide rechten Programme liefen. Geprüfte
Parallelphasen hoch 41,113 s und offen 7,934 s. Fahrrevision
`5506221212b34d7aa9a6dc3e7c06e02b` zur Bedienentscheidung vorgelegt.
