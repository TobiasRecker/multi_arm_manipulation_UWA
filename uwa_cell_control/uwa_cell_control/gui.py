"""Small local UWA preparation GUI, independent of the mobile MuR window."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import signal
import sys
import subprocess

from python_qt_binding import QtCore,QtGui,QtWidgets
from match_ur_hardware.processes import stop_owned_process
from match_ur_hardware.profiles import load_profiles

ARM_IDS=('left_front','left_rear','right_front','right_rear')

LABELS={'left_front':'Links vorne','left_rear':'Links hinten',
        'right_front':'Rechts vorne','right_rear':'Rechts hinten'}


class Window(QtWidgets.QMainWindow):
    def __init__(self,inventory):
        super().__init__()
        self.inventory=Path(inventory).resolve();self.profiles=load_profiles(self.inventory)
        if set(self.profiles)!=set(ARM_IDS):raise ValueError('UWA inventory must define the four cell arms')
        self.drivers={};self.jobs={};self.auxiliary=[];self.state={};self.closing=False
        self.setWindowTitle('UWA · Arme vorbereiten');self.resize(1180,800)
        self.workspace=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
        icon=self.workspace/'src/multi_arm_manipulation_UWA/assets/uwa-cell.png'
        if icon.is_file():self.setWindowIcon(QtGui.QIcon(str(icon)))
        root=QtWidgets.QWidget();self.setCentralWidget(root);layout=QtWidgets.QVBoxLayout(root)
        top=QtWidgets.QHBoxLayout();self.checks={}
        selection=QtWidgets.QGroupBox('Arme auswählen');boxes=QtWidgets.QHBoxLayout(selection)
        for rid in ARM_IDS:
            box=QtWidgets.QCheckBox(LABELS[rid]);box.setChecked(True)
            boxes.addWidget(box);self.checks[rid]=box
        top.addWidget(selection,1)
        self.mode=QtWidgets.QComboBox();self.mode.addItems(['Mock · ohne echte Roboter','Hardware · lokale URs'])
        self.mode.currentIndexChanged.connect(self.change_mode);top.addWidget(self.mode)
        layout.addLayout(top)
        self.banner=QtWidgets.QLabel();self.banner.setWordWrap(True);layout.addWidget(self.banner)
        self.table=QtWidgets.QTableWidget(4,7)
        self.table.setHorizontalHeaderLabels(['Arm','IP','Treiber','Robotermodus','Sicherheit','Programm','Remote'])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setMaximumHeight(175);layout.addWidget(self.table)
        for row,rid in enumerate(ARM_IDS):
            for col,text in enumerate([LABELS[rid],self.profiles[rid]['ip'] or 'nicht konfiguriert','—','—','—','—','—']):
                self.table.setItem(row,col,QtWidgets.QTableWidgetItem(text))
        self.tabs=QtWidgets.QTabWidget();layout.addWidget(self.tabs,1)
        prep=QtWidgets.QWidget();form=QtWidgets.QVBoxLayout(prep)
        self.buttons={}
        for key,text,tip in [
            ('status','Status prüfen','Lesende Abfragen für ausgewählte Arme'),
            ('start','Treiber starten','Lokale ROS-Treiber; kein automatisches Einschalten oder Programmstart'),
            ('prepare','UR bereitstellen','Explizit Motoren einschalten und Bremsen lösen; startet kein Programm'),
            ('play','External Control starten','Nur bei exakt im Inventar hinterlegtem, geladenem Programm'),
            ('drivers_stop','Treiber beenden','Nur die von diesem Fenster gestarteten Treiber beenden')]:
            button=QtWidgets.QPushButton(text);button.setMinimumHeight(40);button.setToolTip(tip)
            button.clicked.connect(lambda checked=False,k=key:self.action(k));form.addWidget(button);self.buttons[key]=button
        info=QtWidgets.QLabel('Bereitstellen, External Control und Bewegungscontroller sind getrennte Schritte.\n'
            'Lokaler Modus oder Sicherheitsstopp: am UR-Pendant prüfen. Die GUI entsperrt nichts automatisch.\n'
            'Noch keine automatischen Referenzfahrten, keine Home-Ziele und kein SSH/rsync.')
        info.setWordWrap(True);form.addWidget(info);form.addStretch()
        edit=QtWidgets.QHBoxLayout()
        for text,callback in [('Inventar öffnen',self.edit_inventory),('Inventar neu laden',self.reload_inventory)]:
            b=QtWidgets.QPushButton(text);b.clicked.connect(callback);edit.addWidget(b)
        form.addLayout(edit);self.tabs.addTab(prep,'Vorbereitung')
        controllers=QtWidgets.QWidget();ctl=QtWidgets.QVBoxLayout(controllers)
        self.tree=QtWidgets.QTreeWidget();self.tree.setHeaderLabels(['Arm / Controller','Zustand'])
        self.tree.header().setSectionResizeMode(0,QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1,QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        ctl.addWidget(self.tree)
        self.controller_note=QtWidgets.QLabel('Wiederverwendet: mur_control · J-PARSE · integrierte Admittanz.\n'
            'Der vorhandene Kollisionscontroller berücksichtigt einen Gegenarm. Ein vollständiges Vierarm-/Tisch-/Werkzeugmodell fehlt hier noch.\n'
            'Hardware-Bewegungsaktivierung bleibt deshalb in dieser ersten Oberfläche gesperrt; Mock-Tests sind verfügbar.')
        self.controller_note.setWordWrap(True);ctl.addWidget(self.controller_note)
        row=QtWidgets.QHBoxLayout()
        for key,text in [('trajectory','Trajektoriencontroller testen · Mock'),('cartesian','Admittanz testen · Mock'),('inactive','Bewegungscontroller deaktivieren'),('rqt','Gelenksteuerung · Mock')]:
            b=QtWidgets.QPushButton(text);b.clicked.connect(lambda checked=False,k=key:self.action(k));row.addWidget(b);self.buttons[key]=b
        ctl.addLayout(row);self.tabs.addTab(controllers,'Controller')
        self.log=QtWidgets.QPlainTextEdit();self.log.setReadOnly(True);self.log.setMaximumBlockCount(1600)
        self.tabs.addTab(self.log,'Protokoll')
        self.stop_button=QtWidgets.QPushButton('STOPP · alle von dieser GUI gestarteten Arme')
        self.stop_button.setMinimumHeight(58);self.stop_button.setStyleSheet('background:#b83333;color:white;font-size:18px;font-weight:bold')
        self.stop_button.setToolTip('Softwarestopp: Controller deaktivieren und UR-Programm stoppen. Kein Hardware-Not-Halt.')
        self.stop_button.clicked.connect(self.stop_all);layout.addWidget(self.stop_button)
        self.footer=QtWidgets.QLabel('Nur lokale Prozesse · getrennt von Gazebo · Status noch nicht geprüft');layout.addWidget(self.footer)
        self.log_path=self.workspace/'setup/logs/uwa-control/gui.log';self.log_path.parent.mkdir(parents=True,exist_ok=True)
        self.timer=QtCore.QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(4000)
        for box in self.checks.values():box.toggled.connect(self.update_buttons)
        self.change_mode();QtCore.QTimer.singleShot(200,self.refresh)

    @property
    def mock(self):return self.mode.currentIndex()==0

    def selected(self):return [rid for rid,box in self.checks.items() if box.isChecked() and box.isEnabled()]

    def note(self,text):
        line=f'{datetime.now().strftime("%H:%M:%S")}  {text}'
        self.log.appendPlainText(line)
        with self.log_path.open('a') as stream:stream.write(line+'\n')

    def change_mode(self):
        self.state.clear();self.tree.clear()
        for rid,box in self.checks.items():
            available=self.mock or bool(self.profiles[rid]['ip'])
            box.setEnabled(available)
            if not available:box.setChecked(False)
        self.banner.setText('MOCK: alle Tests bleiben auf diesem PC; keine Verbindung zu echten URs.' if self.mock else
            'HARDWARE: PC aktuell über WLAN. Treiberstart schaltet nichts ein. Bereitstellen löst nach explizitem Klick die Bremsen. '
            'External-Control-Programm und Werkskinematik je Arm im Inventar konfigurieren.')
        self.banner.setStyleSheet('padding:10px;border-radius:4px;background:#e6eff9;color:#173d62;font-weight:bold' if self.mock else
                                  'padding:10px;border-radius:4px;background:#fff0d5;color:#724800;font-weight:bold')
        self.update_buttons()
        self.render_status()

    def update_buttons(self):
        busy=any(key!='status' for key in self.jobs)
        available=bool(self.selected()) and all(rid in self.drivers for rid in self.selected())
        self.mode.setEnabled(not self.drivers and not busy)
        for key,button in self.buttons.items():
            allowed=not busy
            if key in ('cartesian','trajectory','rqt'):allowed=allowed and self.mock and available
            if key in ('prepare','play'):allowed=allowed and not self.mock and available
            if key=='inactive':allowed=allowed and available
            button.setEnabled(allowed)

    def process(self,args,*,tag,finished=None):
        process=QtCore.QProcess(self)
        process.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.MergedChannels)
        process.setProperty('output','')
        def read():
            chunk=bytes(process.readAllStandardOutput()).decode(errors='replace')
            process.setProperty('output',process.property('output')+chunk)
            if tag!='status' and chunk.strip():self.note(f'[{tag}] {chunk.strip()}')
        process.readyReadStandardOutput.connect(read)
        def done(code,status):
            read()
            if finished:finished(code,process.property('output'))
            process.deleteLater()
        process.finished.connect(done)
        process.errorOccurred.connect(lambda e:self.note(f'{tag}: Prozessfehler {process.errorString()}'))
        process.start('/usr/bin/setsid',['--wait',*args]);return process

    def operation(self,kind,ids=None):
        ids=ids or self.selected()
        if not ids:return
        if kind in self.jobs:return
        mode='mock' if self.mock else 'hardware'
        args=['ros2','run','match_ur_hardware','ur_operation','--inventory',str(self.inventory),
              '--arms',','.join(ids),'--mode',mode,kind]
        def done(code,output):
            self.jobs.pop(kind,None)
            if kind=='status':
                try:
                    line=next(line for line in reversed(output.splitlines()) if line.startswith('{'))
                    data=json.loads(line)
                    if mode==('mock' if self.mock else 'hardware'):
                        for state in data.get('arms',{}).values():state['observed_at']=datetime.now().strftime('%H:%M:%S')
                        self.state.update(data.get('arms',{}));self.render_status()
                except Exception as e:self.note(f'Status konnte nicht gelesen werden: {e}')
            else:
                self.note(f'{kind}: '+('abgeschlossen' if code==0 else 'fehlgeschlagen; Details im Protokoll'))
            self.update_buttons()
        self.jobs[kind]=self.process(args,tag=kind,finished=done);self.update_buttons()

    def render_status(self):
        expanded={self.tree.topLevelItem(i).text(0):self.tree.topLevelItem(i).isExpanded()
                  for i in range(self.tree.topLevelItemCount())}
        self.tree.clear()
        for row,rid in enumerate(ARM_IDS):
            state=self.state.get(rid,{})
            answers={q['command']:q['answer'] for q in state.get('dashboard',{}).get('queries',[])}
            values=['ROS verfügbar' if state.get('driver_available') else 'Startet / keine Antwort' if rid in self.drivers else 'nicht gestartet',
                    'Mock' if self.mock else answers.get('robotmode','—').removeprefix('Robotmode: ').strip(),
                    'Mock' if self.mock else answers.get('safetystatus','—').removeprefix('Safetystatus: ').strip(),
                    'Mock' if self.mock else answers.get('programState','—'),
                    '—' if self.mock else {True:'Ja',False:'Nein'}.get(state.get('dashboard',{}).get('remote_control'),'unbekannt')]
            for col,value in enumerate(values,2):self.table.item(row,col).setText(value)
            for col in range(7):self.table.item(row,col).setToolTip('Letzte Abfrage: '+state.get('observed_at','noch keine'))
            if state.get('dashboard',{}).get('error'):self.table.item(row,2).setText('nicht erreichbar')
            parent=QtWidgets.QTreeWidgetItem([LABELS[rid],''])
            self.tree.addTopLevelItem(parent)
            for c in state.get('controllers',[]):parent.addChild(QtWidgets.QTreeWidgetItem([c['name'],c['state']]))
            parent.setExpanded(expanded.get(LABELS[rid],rid==ARM_IDS[0]))
        observed=max((s.get('observed_at','') for s in self.state.values()),default='')
        self.footer.setText(('Letzte Statusabfrage der Auswahl: '+observed if observed else 'Noch keine Statusdaten')+
                            ' · ROS-Domain 66 · Softwarestopp ersetzt keinen Not-Halt')

    def refresh(self):
        if not self.closing and not self.jobs:self.operation('status')

    def action(self,key):
        ids=self.selected()
        if not ids:self.note('Zuerst mindestens einen konfigurierten Arm auswählen.');return
        if key=='status':self.operation('status');return
        if key=='start':
            for rid in ids:
                if rid in self.drivers:continue
                def done(code,output,rid=rid):
                    self.drivers.pop(rid,None);self.note(f'{LABELS[rid]}: Treiber beendet ({code})');self.update_buttons()
                args=['ros2','launch','uwa_cell_control','arms.launch.py','inventory:='+str(self.inventory),
                      'arms:='+rid,'mode:='+('mock' if self.mock else 'hardware')]
                self.drivers[rid]=self.process(args,tag=rid,finished=done)
            self.update_buttons();return
        if key=='drivers_stop':
            for rid in ids:
                if rid in self.drivers:stop_owned_process(self.drivers[rid])
            return
        if key=='rqt':
            self.auxiliary.append(self.process(['ros2','run','rqt_joint_trajectory_controller','rqt_joint_trajectory_controller'],tag='Gelenksteuerung'));return
        if not all(rid in self.drivers for rid in ids):
            self.note('Diese Aktion benötigt eigene, über diese GUI gestartete Treiber für die Armauswahl.');return
        self.operation(key)

    def stop_all(self):
        ids=list(self.drivers)
        if not ids:self.note('Keine über diese GUI gestarteten Arme zu stoppen.');return
        for key,process in list(self.jobs.items()):
            stop_owned_process(process)
        self.jobs={}
        self.operation('stop',ids)

    def edit_inventory(self):QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.inventory)))

    def reload_inventory(self):
        if self.drivers or self.jobs:
            self.note('Inventar erst nach Beenden der eigenen Treiber/Operationen neu laden.');return
        try:
            self.profiles=load_profiles(self.inventory)
            for row,rid in enumerate(ARM_IDS):self.table.item(row,1).setText(self.profiles[rid]['ip'] or 'nicht konfiguriert')
            self.change_mode();self.note('Inventar neu geladen.')
        except Exception as e:self.note(str(e))

    def closeEvent(self,event):
        self.closing=True;self.timer.stop()
        for p in list(self.jobs.values()):stop_owned_process(p)
        if self.drivers and not self.mock:
            # Explicitly stop programs/controllers before removing owned drivers.
            # Only this GUI's arm set is affected. No automatic power-off.
            try:
                answer=subprocess.run(['ros2','run','match_ur_hardware','ur_operation',
                    '--inventory',str(self.inventory),'--arms',','.join(self.drivers),
                    '--mode','hardware','stop'],capture_output=True,text=True,timeout=25)
                self.note('Schließen: '+answer.stdout[-2000:])
            except Exception as error:self.note(f'Stopp beim Schließen nicht bestätigt: {error}')
        for p in list(self.drivers.values())+self.auxiliary:stop_owned_process(p)
        event.accept()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    ws=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
    parser.add_argument('--inventory',default=str(ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml'))
    args=parser.parse_args()
    os.environ['ROS_DOMAIN_ID']='66';os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
    app=QtWidgets.QApplication([sys.argv[0]])
    app.setDesktopFileName('uwa-control')
    window=Window(args.inventory);window.show()
    signal.signal(signal.SIGINT,lambda *unused:window.close())
    timer=QtCore.QTimer();timer.timeout.connect(lambda:None);timer.start(250)
    return app.exec()
