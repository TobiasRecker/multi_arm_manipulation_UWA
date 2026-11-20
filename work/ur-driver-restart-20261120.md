# N100-UR-Treiber nach ausgeschöpften Dateideskriptoren neu starten

- Status abgeschlossen, 20.11.2026, 14:02 AWST. Die Bedienperson meldete die
  Zelle frei und alle Arme unbeladen. Native RTDE bestätigt bei allen vier
  Armen `RUNNING/NORMAL` und Stillstand über mindestens 0,5 s. Die Motion
  review ist frei von offenen Entscheidungen und Ausführungen.
- Die vier betroffenen `ros2_control_node` hatten unmittelbar vor dem
  Neustart je 1.024 offene Dateideskriptoren am Limit 1.024. Scope ist der
  Neustart genau ihrer vier `uwa-ur-driver-*.service` auf dem N100 bei
  aktivem Schutz. Der normale Bedienpfad für `Start + ROS` ist separat.
- Die vendorte URCL-Quelle kann beim Wiederverbinden den Deskriptor eines
  ungültigen oder abgebrochenen TCP-Sockets überschreiben, ohne ihn zu
  schließen (`src/comm/tcp_socket.cpp`). Das passt zum N100-Befund mit
  997 Sockets ohne Zuordnung in den gelesenen Netzwerktabellen je Treiber.
  Der TCP-Server benutzt `select()` und verwirft Deskriptoren ab
  `FD_SETSIZE`. Eine Änderung des Prozesslimits ist keine dauerhafte Behebung.
- Um 13:59:57 waren alle vier Treiberprozesse neu und an den acht
  vorgesehenen Ports erreichbar, je 30 Dateideskriptoren. Schutz- und
  Greiferdienst behielten ihre Dienstidentitäten. RTDE bestätigte alle vier
  `RUNNING/NORMAL/STOPPED` und stationär. Die Haltecontroller sind inaktiv
  provisioniert. Bedienhandlung **Start + ROS** steht aus.
- Dauerhafter Stand und Prüfnachweise im [Zell-Handover](../HANDOVER.md).
