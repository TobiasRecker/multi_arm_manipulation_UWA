"""Responsive Qt session UI. Motion ownership lives in the separate ROS backend."""
import json,os,sys,threading,time
# VS Code's Snap terminal can inject incompatible GTK/GIO libraries into a
# system Qt process. Remove only Snap-specific module overrides in this GUI.
for _name in ('GTK_PATH','GTK_EXE_PREFIX','GTK_IM_MODULE_FILE','GIO_MODULE_DIR'):
    if '/snap/' in os.environ.get(_name,''):os.environ.pop(_name,None)
import numpy as np
from scipy.spatial.transform import Rotation
from python_qt_binding import QtCore,QtGui,QtWidgets
import rclpy
from rclpy.executors import SingleThreadedExecutor
from .client import Client
from uwa_cell_gazebo.configuration import ROBOT_IDS

NAMES={'left_front':'Links vorne','left_rear':'Links hinten','right_front':'Rechts vorne','right_rear':'Rechts hinten'}

class Window(QtWidgets.QMainWindow):
    def __init__(self,node):
        super().__init__();self.node=node;self.closing=False;self.close_started=None;self.stamps={}
        self.allow_close=False;self.pause_pending=False;self.world_paused=False
        self.setWindowTitle('UWA Hand-Auge-Kalibrierung | Simulation');self.resize(1200,850)
        central=QtWidgets.QWidget();self.setCentralWidget(central);layout=QtWidgets.QVBoxLayout(central)
        title=QtWidgets.QLabel('Hand-Auge-Kalibrierung der UWA-Zelle')
        title.setStyleSheet('font-size:22px; font-weight:600;');layout.addWidget(title)
        layout.addWidget(QtWidgets.QLabel('Simulation · diagonale Paare parallel · Wartearme parken · getrenntes kalibriertes Modell'))
        selection=QtWidgets.QHBoxLayout();self.robots={}
        for rid in ROBOT_IDS:
            box=QtWidgets.QCheckBox(NAMES[rid]);box.setChecked(True);self.robots[rid]=box;selection.addWidget(box)
        self.diagonal=QtWidgets.QCheckBox('Diagonalpaare');self.diagonal.setChecked(True)
        self.diagonal.setToolTip('Links vorne + rechts hinten, danach links hinten + rechts vorne. Andere Arme werden vorher geparkt.')
        selection.addWidget(self.diagonal);selection.addStretch();selection.addWidget(QtWidgets.QLabel('Stellungen je Arm:'))
        self.count=QtWidgets.QSpinBox();self.count.setRange(30,50);self.count.setValue(40);selection.addWidget(self.count);layout.addLayout(selection)
        buttons=QtWidgets.QHBoxLayout()
        self.prepare_button=QtWidgets.QPushButton('1  Posen vorbereiten');self.prepare_button.clicked.connect(self.prepare)
        self.start_button=QtWidgets.QPushButton('2  Start');self.start_button.clicked.connect(node.start)
        self.pause_button=QtWidgets.QPushButton('Pause');self.pause_button.clicked.connect(lambda:node.command('resume' if node.state.get('phase')=='PAUSED' else 'pause'))
        self.stop_button=QtWidgets.QPushButton('STOPP');self.stop_button.setMinimumHeight(48)
        self.stop_button.setStyleSheet('background:#bb1825; color:white; font-size:20px; font-weight:bold; padding:8px 28px;')
        self.stop_button.clicked.connect(lambda:node.command('stop'))
        self.world_button=QtWidgets.QPushButton('Simulation pausieren');self.world_button.clicked.connect(self.pause_world)
        self.apply_button=QtWidgets.QPushButton('3  Ergebnis übernehmen');self.apply_button.clicked.connect(self.apply)
        for widget in (self.prepare_button,self.start_button,self.pause_button,self.stop_button,self.world_button,self.apply_button):buttons.addWidget(widget)
        layout.addLayout(buttons)
        self.status_label=QtWidgets.QLabel('Warte auf Kalibrierungsbackend …');self.status_label.setWordWrap(True);layout.addWidget(self.status_label)
        self.progress=QtWidgets.QProgressBar();layout.addWidget(self.progress)
        grid=QtWidgets.QGridLayout();self.views={};self.view_groups={}
        for index,rid in enumerate(ROBOT_IDS):
            group=QtWidgets.QGroupBox(NAMES[rid]);box=QtWidgets.QVBoxLayout(group)
            self.view_groups[rid]=group
            image=QtWidgets.QLabel('Warte auf Kamerabild');image.setMinimumSize(300,180);image.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            image.setStyleSheet('background:#19212c; color:#dfe7ee;');box.addWidget(image)
            self.views[rid]=image;grid.addWidget(group,index//2,index%2)
        self.tabs=QtWidgets.QTabWidget();live_page=QtWidgets.QWidget();live_page.setLayout(grid)
        self.tabs.addTab(live_page,'Livebilder')
        result_page=QtWidgets.QWidget();result_layout=QtWidgets.QVBoxLayout(result_page)
        self.results=QtWidgets.QPlainTextEdit();self.results.setReadOnly(True)
        self.result_table=QtWidgets.QTableWidget(0,5)
        self.result_table.setHorizontalHeaderLabels(['Ergebnis','XYZ [mm]','Roll / Pitch / Yaw [°]','Qualität / Abstand','Ground Truth'])
        self.result_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        result_layout.addWidget(self.result_table,stretch=1);result_layout.addWidget(self.results)
        self.tabs.addTab(result_page,'Ergebnisse');layout.addWidget(self.tabs,stretch=1)
        self.results.setMaximumHeight(65)
        self.info=QtWidgets.QLabel('Vor Start rqt-Ausgabe deaktivieren. Stopp hält die aktuelle Stellung; keine automatische Rückfahrt nach Abbruch.')
        self.info.setWordWrap(True);layout.addWidget(self.info)
        self.timer=QtCore.QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(100)
        self.last_result=''

    def prepare(self):
        self.tabs.setCurrentIndex(0)
        self.node.prepare([r for r,b in self.robots.items() if b.isChecked()],self.count.value(),self.diagonal.isChecked())

    def pause_world(self):
        # Direct transport request is independent of the motion backend's process.
        self.node.command('stop')
        def call():
            try:
                from gz.transport import Node
                from gz.msgs.world_control_pb2 import WorldControl
                from gz.msgs.boolean_pb2 import Boolean
                transport=Node();ok,response=transport.request('/world/uwa_lab/control',WorldControl(pause=True),WorldControl,Boolean,1000)
                self.world_paused=bool(ok and response.data)
            except Exception as error:self.node.error=f'Gazebo-Pause fehlgeschlagen: {error}'
        threading.Thread(target=call,daemon=True).start()

    def apply(self):
        answer=QtWidgets.QMessageBox.question(self,'Kalibriertes Modell aktivieren',
          'Das geprüfte Profil wird aktiv und ersetzt das getrennte kalibrierte TF-/Planungsmodell.\n'
          'Die Roboterpositionen in Gazebo und Ground Truth bleiben unverändert.\n\nÜbernehmen?',
          QtWidgets.QMessageBox.StandardButton.Yes|QtWidgets.QMessageBox.StandardButton.No,QtWidgets.QMessageBox.StandardButton.No)
        if answer==QtWidgets.QMessageBox.StandardButton.Yes:self.node.apply()

    def refresh(self):
        self.node.pulse()
        state=self.node.state;phase=state.get('phase','OFFLINE')
        owns=state.get('client_id')==self.node.client_id
        online=time.monotonic()-self.node.last_status<1.5
        busy=phase in ('RESTORING','PREPARING','RUNNING','PARKING','POSITIONING','MOVING','SETTLING','CAPTURING','RETURNING','HALTING','PAUSED','SOLVING','APPLYING')
        if busy and owns and time.monotonic()-self.node.last_status>1.5 and not self.pause_pending:
            self.pause_pending=True;self.pause_world();self.node.error='Backend verloren; Gazebo-Pause angefordert'
        self.prepare_button.setEnabled(online and not busy and bool(state))
        self.start_button.setEnabled(online and phase=='READY' and owns)
        self.pause_button.setEnabled(online and owns and phase in ('MOVING','PARKING','POSITIONING','RUNNING','SETTLING','CAPTURING','RETURNING','PAUSED'))
        self.pause_button.setText('Fortsetzen' if phase=='PAUSED' else 'Pause')
        fits=state.get('summary',{})
        passed=bool(fits) and all(f.get('passed',False) for f in fits.values())
        self.apply_button.setEnabled(online and passed and phase=='COMPLETE' and bool(state.get('result_path')) and state.get('stopped',False))
        for box in self.robots.values():box.setEnabled(not busy)
        self.count.setEnabled(not busy)
        self.diagonal.setEnabled(not busy)
        names=' + '.join(NAMES.get(r,r) for r in state.get('active_robots',[])) or NAMES.get(state.get('robot_id'),'')
        step=f" | Schritt {state['stage_index']}/{state['stage_total']}" if state.get('stage_total') else ''
        self.status_label.setText(f"{phase} | {names}{step} | {state.get('message','Backend nicht erreichbar')}"+
                                  f" | Verworfen: {state.get('rejected',0)}"+
                                  (f"\n{self.node.error}" if self.node.error else ''))
        counts=state.get('counts',{});total=state.get('progress_total') or state.get('target',40)*max(1,len(counts))
        self.progress.setRange(0,total);self.progress.setValue(sum(counts.values()))
        for rid,label in self.views.items():
            quality=state.get('camera_quality',{}).get(rid,{})
            count_text=f" · {state['counts'][rid]}/{state.get('target',40)}" if rid in state.get('counts',{}) else ''
            parked=' · geparkt' if rid in state.get('parked_robots',[]) else ''
            self.view_groups[rid].setTitle(NAMES[rid]+count_text+parked+f" · {quality.get('corners',0)} Ecken"+
              (f" · RMS {quality['reprojection_rms_px']:.3f} px" if 'reprojection_rms_px' in quality else ' · Board nicht erkannt'))
            msg=self.node.images.get(rid)
            if msg is None:continue
            stamp=(msg.header.stamp.sec,msg.header.stamp.nanosec)
            if self.stamps.get(rid)==stamp:continue
            self.stamps[rid]=stamp
            image=QtGui.QImage(bytes(msg.data),msg.width,msg.height,msg.step,QtGui.QImage.Format.Format_RGB888).rgbSwapped().copy()
            label.setPixmap(QtGui.QPixmap.fromImage(image).scaled(label.size(),QtCore.Qt.AspectRatioMode.KeepAspectRatio,QtCore.Qt.TransformationMode.SmoothTransformation))
        if state.get('result_path'):
            report={'Ergebnisdatei':state['result_path'],'Aktives Profil':state.get('active_profile',''),
                    'summary':state.get('summary',{}),'pairs':state.get('relative_bases',{}),'truth':state.get('ground_truth',{})}
            text=json.dumps(report,sort_keys=True)
            if text!=self.last_result:
                self.results.setPlainText('Ergebnis: '+state['result_path']+'\nAktives Profil: '+state.get('active_profile','')+'\nStreuung ist keine Zusage absoluter Genauigkeit.')
                rows=[]
                for rid,fit in state.get('summary',{}).items():
                    matrix=np.asarray(fit['T_tool0_camera']);quality=fit['validation']
                    gt=state.get('ground_truth',{}).get('robots',{}).get(rid,{}).get('handeye_error',{})
                    quality_text=f"Val: {quality['median_reprojection_rms_px']:.3f} px / {quality['board_translation_rms_m']*1000:.2f} mm / {quality['board_rotation_rms_deg']:.3f}°"
                    repeat=fit.get('handeye_repeatability')
                    if repeat:quality_text+='; Bootstrap σ XYZ [mm]: '+' / '.join(f'{v:.3f}' for v in repeat['translation_std_mm'])
                    rows.append([NAMES[rid]+' Kamera an tool0',matrix,
                                 quality_text,
                                 f"{gt.get('translation_m',0)*1000:.2f} mm / {gt.get('rotation_deg',0):.3f}°"])
                for rid,matrix in state.get('table_bases',{}).items():
                    rows.append([NAMES[rid]+' Basis im Tisch',np.asarray(matrix),'abhängig von konfigurierter Boardpose',''])
                for table,pair in state.get('relative_bases',{}).items():
                    gt=state.get('ground_truth',{}).get('relative_bases',{}).get(table,{})
                    interval=pair.get('distance_bootstrap_interval_mm')
                    label=f"Abstand {pair['distance_mm']:.2f} mm"
                    if interval:label+=f"; 95%-Streuung {interval[0]:.2f}–{interval[1]:.2f}"
                    rows.append([('Links' if table=='left' else 'Rechts')+' vorne → hinten',np.asarray(pair['T_front_rear']),label,
                                 f"{gt.get('translation_m',0)*1000:.2f} mm / {gt.get('rotation_deg',0):.3f}°"])
                self.result_table.setRowCount(len(rows))
                for i,(label,matrix,quality,truth) in enumerate(rows):
                    values=[label,' / '.join(f'{v:.2f}' for v in matrix[:3,3]*1000),
                            ' / '.join(f'{v:.2f}' for v in Rotation.from_matrix(matrix[:3,:3]).as_euler('xyz',degrees=True)),quality,truth]
                    for j,value in enumerate(values):
                        item=QtWidgets.QTableWidgetItem(value);item.setToolTip(value);self.result_table.setItem(i,j,item)
                self.last_result=text
                self.tabs.setCurrentIndex(1)
        elif self.last_result:
            self.last_result='';self.result_table.setRowCount(0)
            self.tabs.setCurrentIndex(0)
            self.results.setPlainText('Aktives Profil: '+state.get('active_profile','keines'))
        if self.closing and (phase in ('STOPPED','IDLE','READY','COMPLETE','ERROR') and state.get('stopped')):
            self.allow_close=True;self.closing=False;self.timer.stop();self.close()
        elif self.closing and time.monotonic()-self.close_started>3:
            if not self.pause_pending:self.pause_pending=True;self.pause_world()
            if self.world_paused:self.allow_close=True;self.closing=False;self.timer.stop();self.close()

    def closeEvent(self,event):
        if self.node.state.get('client_id')!=self.node.client_id:event.accept();return
        if self.allow_close:event.accept();return
        if self.close_started is None and not self.closing and self.node.state.get('phase') not in ('MOVING','PARKING','POSITIONING','RUNNING','SETTLING','CAPTURING','RETURNING','PREPARING','SOLVING','PAUSED','HALTING','APPLYING'):
            event.accept();return
        if not self.closing:
            self.closing=True;self.close_started=time.monotonic();self.node.command('stop')
        event.ignore()


def main():
    if os.environ.get('ROS_DOMAIN_ID')!='64':raise SystemExit('Source scripts/env.bash: simulation domain 64 required')
    rclpy.init();node=Client();executor=SingleThreadedExecutor();executor.add_node(node)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
    app=QtWidgets.QApplication(sys.argv);window=Window(node);window.show()
    try:app.exec()
    finally:
        if node.state.get('client_id')==node.client_id:node.command('stop');time.sleep(.2)
        window.timer.stop();executor.shutdown(timeout_sec=2);thread.join(timeout=2)
        node.destroy_node();rclpy.shutdown()
