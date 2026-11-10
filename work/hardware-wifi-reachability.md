# Reale Geräte über WLAN erreichen

- Agent/Aufgabe: Codex OAK-/Hardware-Gespräch, `hardware-wifi-reachability`.
- Status: **abgeschlossen**.
- Aktualisiert: 2026-11-10, Australia/Perth.
- Nutzerzuordnung: `right_rear` =192.168.8.170, `right_front` =192.168.8.103;
  „erster/zweiter“ sind zufällige Nummern, keine dauerhaften Arm-IDs.
  OAK4-D R9 =192.168.8.238.
- Vorübergehend PC per WLAN wegen defektem langem LAN-Kabel; Geräte weiterhin
  kabelgebunden am Router. Geringere Bandbreite/höhere Latenz berücksichtigen.
- Umfang: IP-Route, ICMP-Latenz/Verlust, nur lesende UR-Dashboard-Abfragen,
  OAK-Infos und gegebenenfalls kleiner Kamerastream. Keine Robotertreiber starten,
  keine Bewegung, keine Power-/Brake-/Programm-/Remote-Modusänderung.
- Bereiche: Diagnoseartefakte unter Workspace `setup/`, Inventar/Anforderungen
  in Dokumentation; Simulationslayout und bestehende Dienste erhalten.
- Ergebnis: drei Geräte erfolgreich überwlp88s0f0/PC192.168.8.209 erreicht.
  UR-Dashboard sieben lesende Antworten je Arm; Seriennummern dokumentiert.
  Je40 Pings ohne Verlust, Mittel5,0–6,9ms, Maximum45,8ms. OAK-Agentinfos
  und640×480NV12@5fps (gemessen4,997fps) erfolgreich, danach geschlossen.
- Inventar `config/hardware_inventory.yaml`, Bericht
  `docs/hardware_network_2026-11-10.md`, Rohdaten unter Workspace
  `setup/logs/hardware-wifi-2026-11-10/`. Root-/Projekt-/OAK-Handover und Regeln
  aktualisiert. Keine Echtzeitregelungsfreigabe oder Hardwarebewegung behauptet.
