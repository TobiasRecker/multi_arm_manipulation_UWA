# Reale Geräte über WLAN: Erreichbarkeitsprüfung

Geprüft am **2026-11-10**, etwa12:45–12:49 Australia/Perth. Es wurden nur
Dashboard-Informationen gelesen und ein kurzer, begrenzter Kamerastream geprüft.
Keine Robotertreiber gestartet, keine Gelenkziele oder Power-/Brake-/Programm-/
Remote-Modusänderungen gesendet. Bestehende Netzwerkkonfiguration erhalten.

## Feste Gerätezuordnung

Nutzerzuordnung und ausgelesene Seriennummern sind im separaten
[`config/hardware_inventory.yaml`](../config/hardware_inventory.yaml) festgehalten.
Die Reihenfolge „erster/zweiter“ ist zufällig und darf keine Arm-ID ersetzen.

| Arm/Gerät | IP | Bestätigt |
|---|---|---|
| **right_rear**, hinten rechts | **192.168.8.170** | UR-Dashboard29999, Seriennummer20195501620 |
| **right_front**, vorne rechts | **192.168.8.103** | UR-Dashboard29999, Seriennummer20195501617 |
| OAK4-D R9 | **192.168.8.238** | oakctl-Geräteinfos und DepthAI-Bildstream |

Beide UR-Dashboards melden `UR5`, Software `5.10.1.106310`. Den Dashboard-
Modellfamiliennamen wörtlich speichern; die Simulation verwendet UR5e rechts.
Status zum Abfragezeitpunkt jeweils `POWER_OFF`, `NORMAL`, Programm
`STOPPED <unnamed>`, `is in remote control = false`. Das sind ausgelesene
Momentaufnahmen, keine von dieser Prüfung gesetzten Betriebszustände.

Verwendete lesende Dashboard-Abfragen: `PolyscopeVersion`, `get robot model`,
`get serial number`, `robotmode`, `safetystatus`, `programState`,
`is in remote control`. Alle sieben Antworten je Roboter erfolgreich.
[Offizielle Dashboard-Befehle](https://www.universal-robots.com/manuals/EN/HTML/SW5_25_1/Content/prod-dashboard/Dashboard_table.htm).

## Aktueller Netzwerkweg

PC laut Nutzer vorübergehend über WLAN, weil das lange PC-Router-LAN-Kabel
defekt ist; Roboter und Kamera bleiben kabelgebunden am Router.
Tatsächlich ausgelesen:

- PC **192.168.8.209/24**, WLAN **wlp88s0f0**; alle drei Zielrouten über WLAN.
- Gateway192.168.8.1, Ethernet **enp87s0 DOWN**. Frühere PC-Adresse192.168.8.243
  und2,5-Gbit-Ethernet-Messungen sind für diesen Test nicht die aktuelle Verbindung.
- WLAN5180MHz / Kanal36 /5GHz, Signal bei einer Stichprobe−48dBm.
- Ausgehandelte Funkraten bei der Stichprobe RX576,4 / TX1080,6Mbit/s.
  **Keine gemessene Nutzdatenbandbreite**; die Anzeige des AP von1170Mbit/s ist
  ebenfalls kein Durchsatznachweis. Kein maximaler Bandbreiten-/Lasttest ausgeführt.

## Latenz und Verlust

Je40 kleine ICMP-Echo-Abfragen mit0,25s Abstand, Dauer ungefähr10s:

| Ziel | Verlust | RTT min / Mittel / Maximum | p95 (Stichprobe) |
|---|---:|---:|---:|
| right_rear | 0/40 | 1,794 /6,872 /30,920ms | 24,4ms |
| right_front | 0/40 | 1,716 /5,024 /45,818ms | 9,32ms |
| OAK4 | 0/40 | 2,282 /6,521 /14,517ms | 12,8ms |

Dashboard-Verbindungsaufbau ca3,1/1,9ms; Abfrageantworten jeweils ca1,8–6,7ms.
Diese Werte zeigen Erreichbarkeit und kurze Momentaufnahmen, keine garantierten
Latenzen, langfristige Verlustfreiheit oder geprüfte Echtzeit-Roboterausführung.

## Kamera: kleiner WLAN-Bildtest

oakctl bestätigt **Luxonis, Inc. OAK4-D R9**, Serien-/Geräte-ID1479883285,
Luxonis OS RVC4 **1.32.1**, Agent **0.20.0**. Die Kamera meldet weiterhin
eth0/192.168.8.238; DepthAI nennt dasselbe Gerät **OAK-4-PRO / RVC4**.

Angefordert640×480,NV12,5fps. Nach3s Einlaufzeit52 Frames in10,21s erfasst:
**4,997fps**, tatsächlich640×480, etwa18,9Mbit/s Bildnutzdaten nach der
Messzählung (ohne Transport-/WLAN-Overhead). Ein Frame als PNG gespeichert.
Verbindung danach sauber geschlossen; kein dauerhafter Stream gestartet.
Der eigene alte Livedienst war bereits vor dem Test inaktiv; Simulation ebenfalls.

Für die WLAN-Übergangsphase zunächst kleine Bildprofile verwenden; höher
auflösende Kalibrierbilder gezielt und bei Stillstand aufnehmen. Zeitstempel,
Jitter und Verbindungszustand bei einer späteren Roboterintegration berücksichtigen.
Die jetzige PC-Adresse muss bei späteren Rückverbindungen berücksichtigt werden;
an URCaps/Controller-/Treiberadressen wurde hier nichts verändert.

## Nachweise

Lokale Artefakte unter `~/UWA_ws/setup/logs/hardware-wifi-2026-11-10/`:
`report.json`, `ur-dashboard.json`, drei `ping_*.log`, `ping-summary.json`,
`oak-info.json`, `oak-stream.json`, `oak-wifi-test.png`.
Rohbilder und vollständige lokale Diagnoseartefakte werden nicht ins Git übernommen.
Dieses Inventar startet keine echte Hardware und gehört nicht ins Simulationslaunch.
