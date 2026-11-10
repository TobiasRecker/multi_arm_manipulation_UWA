"""Small local UWA preparation GUI, independent of the mobile MuR window."""
import argparse
from datetime import datetime
import json
import math
import os
from pathlib import Path
import signal
import sys

from python_qt_binding import QtCore,QtGui,QtWidgets
from match_ur_hardware.processes import stop_owned_process
from match_ur_hardware.profiles import load_profiles
from .session_logs import SessionLogs
from .feedback import ActionFeedback

ARM_IDS=('left_front','left_rear','right_front','right_rear')

LABELS={'left_front':'Left front','left_rear':'Left rear',
        'right_front':'Right front','right_rear':'Right rear'}


class LogExport(QtCore.QThread):
    saved=QtCore.Signal(str)
    failed=QtCore.Signal(str)

    def __init__(self,session,metadata,parent):
        super().__init__(parent);self.session=session;self.metadata=metadata

    def run(self):
        try:self.saved.emit(str(self.session.export(self.metadata)))
        except Exception as error:self.failed.emit(str(error))


class Window(QtWidgets.QMainWindow):
    def __init__(self,inventory,*,arms=None,mode='mock'):
        super().__init__()
        self.inventory=Path(inventory).resolve();self.profiles=load_profiles(self.inventory)
        if set(self.profiles)!=set(ARM_IDS):raise ValueError('UWA inventory must define the four cell arms')
        self.drivers={};self.jobs={};self.auxiliary=[];self.state={};self.closing=False
        self.jog_dialogs={}
        self.setWindowTitle('UWA · Direct UR Test');self.resize(1180,900)
        self.manual_key=None;self.manual_title='';self.start_ids=[];self.manual_pending=False;self.click_sequence=0
        self.workspace=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
        self.session=SessionLogs(self.workspace,namespace=next(iter(self.profiles.values()))['namespace_root'])
        self.export_worker=None;self.close_after_export=False
        icon=self.workspace/'src/multi_arm_manipulation_UWA/assets/uwa-cell.png'
        if icon.is_file():self.setWindowIcon(QtGui.QIcon(str(icon)))
        root=QtWidgets.QWidget();self.setCentralWidget(root);layout=QtWidgets.QVBoxLayout(root)
        top=QtWidgets.QHBoxLayout();self.checks={}
        selection=QtWidgets.QGroupBox('Select arms');boxes=QtWidgets.QHBoxLayout(selection)
        for rid in ARM_IDS:
            box=QtWidgets.QCheckBox(LABELS[rid]);box.setChecked(rid in (arms if arms is not None else ('right_rear',)))
            boxes.addWidget(box);self.checks[rid]=box
        top.addWidget(selection,1)
        self.mode=QtWidgets.QComboBox();self.mode.addItems(['Mock · no physical robots','Hardware · local URs'])
        self.mode.currentIndexChanged.connect(self.change_mode);top.addWidget(self.mode)
        layout.addLayout(top)
        self.banner=QtWidgets.QLabel();self.banner.setWordWrap(True);layout.addWidget(self.banner)
        self.feedback=ActionFeedback();layout.addWidget(self.feedback)
        self.table=QtWidgets.QTableWidget(4,7)
        self.table.setHorizontalHeaderLabels(['Arm','IP','Driver','Robot mode','Safety','Program','Remote'])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setFixedHeight(170);layout.addWidget(self.table)
        for row,rid in enumerate(ARM_IDS):
            for col,text in enumerate([LABELS[rid],self.profiles[rid]['ip'] or 'not configured','—','—','—','—','—']):
                self.table.setItem(row,col,QtWidgets.QTableWidgetItem(text))
        self.tabs=QtWidgets.QTabWidget();layout.addWidget(self.tabs,1)
        prep=QtWidgets.QWidget();form=QtWidgets.QVBoxLayout(prep)
        actions=QtWidgets.QGridLayout();form.addLayout(actions)
        self.buttons={}
        for index,(key,text,tip) in enumerate([
            ('status','Check status','Read-only queries for the selected arms'),
            ('start','Start drivers','Local ROS drivers; no automatic power-on or program start'),
            ('load','Load broadcasters / controllers','Retry an incomplete startup; motion controllers are loaded inactive'),
            ('joints','Read joint angles','Receive JointState only; no External Control program required'),
            ('prepare','Prepare UR','Power on and release brakes explicitly; does not start a program'),
            ('play','Start loaded UR program','The UR Dashboard starts the currently loaded program'),
            ('drivers_stop','Stop drivers','Stop only the drivers started by this window')]):
            button=QtWidgets.QPushButton(text);button.setMinimumHeight(40);button.setToolTip(tip)
            button.clicked.connect(lambda checked=False,k=key:self.action(k));actions.addWidget(button,index//2,index%2);self.buttons[key]=button
        jog=QtWidgets.QPushButton('Cartesian jog…');jog.setMinimumHeight(40)
        jog.clicked.connect(lambda:self.action('jog'));actions.addWidget(jog,3,1);self.buttons['jog']=jog
        info=QtWidgets.QLabel('Preparation, External Control and motion controllers are separate steps.\n'
            'Local mode or safety stop: check the UR pendant. The GUI does not automatically unlock it.\n'
            'No automatic reference moves, home targets or SSH/rsync.')
        info.setWordWrap(True);form.addWidget(info);form.addStretch()
        edit=QtWidgets.QHBoxLayout()
        for text,callback in [('Open inventory',self.edit_inventory),('Reload inventory',self.reload_inventory)]:
            b=QtWidgets.QPushButton(text);b.clicked.connect(callback);edit.addWidget(b)
            b.pressed.connect(lambda b=b:self.acknowledge(b.text(),b.text(),b))
        form.addLayout(edit);self.tabs.addTab(prep,'Preparation')
        controllers=QtWidgets.QWidget();ctl=QtWidgets.QVBoxLayout(controllers)
        self.tree=QtWidgets.QTreeWidget();self.tree.setHeaderLabels(['Arm / controller','State'])
        self.tree.header().setSectionResizeMode(0,QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1,QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        ctl.addWidget(self.tree)
        self.controller_note=QtWidgets.QLabel('Reused: mur_control · J-PARSE · integrated admittance.\n'
            'The existing collision controller models one other arm. Full four-arm/table/tool collision integration is pending.\n'
            'Direct driver control: no additional Dashboard, program-state or arm-count gates.')
        self.controller_note.setWordWrap(True);ctl.addWidget(self.controller_note)
        row=QtWidgets.QHBoxLayout()
        for key,text in [('trajectory','Activate trajectory controller'),('cartesian','Activate admittance'),('inactive','Deactivate motion controllers'),('rqt','Joint control · rqt')]:
            b=QtWidgets.QPushButton(text);b.clicked.connect(lambda checked=False,k=key:self.action(k));row.addWidget(b);self.buttons[key]=b
        ctl.addLayout(row);self.tabs.addTab(controllers,'Controller')
        self.joints=QtWidgets.QPlainTextEdit();self.joints.setReadOnly(True)
        self.joints.setPlainText('Read joint angles: receive JointState independently of the Dashboard program state.')
        self.tabs.addTab(self.joints,'Joint angles')
        self.log=QtWidgets.QPlainTextEdit();self.log.setReadOnly(True);self.log.setMaximumBlockCount(1600)
        self.tabs.addTab(self.log,'Log')
        self.stop_button=QtWidgets.QPushButton('STOP · selected and owned arms')
        self.stop_button.setMinimumHeight(58);self.stop_button.setStyleSheet('background:#8a0909;color:white;border:3px solid #280000;font-size:18px;font-weight:bold')
        self.stop_button.setToolTip('Software stop: deactivate controllers and stop the UR program. Not a hardware emergency stop.')
        self.stop_button.clicked.connect(self.stop_all);layout.addWidget(self.stop_button)
        exports=QtWidgets.QHBoxLayout()
        self.save_logs_button=QtWidgets.QPushButton('Save logs')
        self.save_logs_button.setToolTip('Save this session, process output, related ROS logs and a status snapshot locally')
        self.save_logs_button.clicked.connect(self.save_logs);exports.addWidget(self.save_logs_button)
        self.export_label=QtWidgets.QLabel('Session logs: '+self.session.id)
        self.export_label.setWordWrap(True);self.export_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        exports.addWidget(self.export_label,1);layout.addLayout(exports)
        self.footer=QtWidgets.QLabel('Local processes only · separate from Gazebo · status not checked yet');layout.addWidget(self.footer)
        self.log_path=self.session.gui_log
        for key,button in [*self.buttons.items(),('stop',self.stop_button),('save',self.save_logs_button)]:
            button.pressed.connect(lambda key=key,button=button:self.acknowledge(key,button.text(),button))
        self.timer=QtCore.QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(4000)
        for box in self.checks.values():box.toggled.connect(self.update_buttons)
        self.mode.setCurrentIndex(0 if mode=='mock' else 1)
        self.change_mode();QtCore.QTimer.singleShot(200,self.refresh)
        self.note('Session started: '+self.session.id)

    @property
    def mock(self):return self.mode.currentIndex()==0

    def selected(self):return [rid for rid,box in self.checks.items() if box.isChecked() and box.isEnabled()]

    def note(self,text):
        line=f'{datetime.now().strftime("%H:%M:%S")}  {text}'
        self.log.appendPlainText(line)
        self.session.note(line)

    def acknowledge(self,key,title,button):
        self.manual_key=key;self.manual_title=title;self.manual_pending=True
        self.feedback.show_state('RECEIVED',title,'Click received · '+datetime.now().strftime('%H:%M:%S'))
        self.note('Button pressed: '+title)
        if button.property('feedback_base') is None:button.setProperty('feedback_base',button.styleSheet())
        original=button.property('feedback_base');self.click_sequence+=1;sequence=self.click_sequence
        button.setProperty('feedback_sequence',sequence)
        colour='#560000' if key=='stop' else '#123f85'
        button.setStyleSheet(f'QPushButton {{background:{colour};color:white;border:4px solid black;font-weight:bold;}}')
        button.repaint()
        def restore():
            try:
                if button.property('feedback_sequence')==sequence:button.setStyleSheet(original)
            except RuntimeError:pass  # Window may already have closed.
        QtCore.QTimer.singleShot(1200,restore)

    def action_result(self,key,ok,detail=''):
        if self.manual_key==key:
            self.manual_pending=False
            self.feedback.show_state('DONE' if ok else 'FAILED',self.manual_title,detail)
            self.note(f'Action {"completed" if ok else "failed"}: {self.manual_title} · {detail}')

    @staticmethod
    def error_detail(output):
        try:
            data=json.loads(next(line for line in reversed(output.splitlines()) if line.startswith('{')))
            return data.get('error') or '; '.join(f'{rid}: {arm["error"]}' for rid,arm in data.get('arms',{}).items() if arm.get('error'))
        except (ValueError,StopIteration):
            if 'already managed in this domain' in output:
                return 'An older launch still owns this arm. Its controller manager may have exited; stop that failed launch before retrying.'
            return next((line for line in reversed(output.splitlines()) if '[ERROR]' in line),output[-600:])

    def save_logs(self):
        if self.export_worker is not None:return
        self.note('Saving session logs…')
        if self.manual_key=='save':self.feedback.show_state('RUNNING','Save logs','Creating a diagnostic archive in the background.')
        self.grab().save(str(self.session.directory/'gui.png'))
        metadata={'inventory_path':str(self.inventory),'mode':'mock' if self.mock else 'hardware',
            'action_feedback':{'phase':self.feedback.phase,'title':self.feedback.message,'detail':self.feedback.full_detail},
            'selected_arms':self.selected(),'status':self.state,
            'jog_dialogs':{rid:dialog.snapshot() for rid,dialog in self.jog_dialogs.items()},
            'driver_pids':{rid:int(p.processId()) for rid,p in self.drivers.items()},
            'operation_pids':{key:int(p.processId()) for key,p in self.jobs.items()},
            'profiles':{rid:{key:arm.get(key) for key in ['ip','ur_type','namespace','prefix','ports',
                'joint_names','kinematics_file','external_control_program','compliance_enabled']} for rid,arm in self.profiles.items()}}
        # Detach mutable UI state before the worker starts. No Qt objects in the archive.
        metadata=json.loads(json.dumps(metadata))
        worker=LogExport(self.session,metadata,self);self.export_worker=worker
        self.save_logs_button.setEnabled(False);self.export_label.setText('Saving logs…')
        def saved(path):
            self.export_label.setText('Saved: '+path);self.export_label.setToolTip(path)
            self.note('Logs saved: '+path)
            self.action_result('save',True,path)
        def failed(error):
            self.export_label.setText('Could not save logs: '+error);self.note('Log export failed: '+error)
            self.action_result('save',False,error)
        def finished():
            self.export_worker=None;self.save_logs_button.setEnabled(True);worker.deleteLater()
            if self.close_after_export:self.close()
        worker.saved.connect(saved);worker.failed.connect(failed);worker.finished.connect(finished)
        worker.start()

    def change_mode(self):
        for dialog in list(self.jog_dialogs.values()):dialog.close()
        self.state.clear();self.tree.clear()
        for rid,box in self.checks.items():
            available=self.mock or bool(self.profiles[rid]['ip'])
            box.setEnabled(available)
            if not available:box.setChecked(False)
        self.banner.setText('MOCK: all tests stay on this PC; no connection to physical URs.' if self.mock else
            'HARDWARE · direct test: Prepare, start programs and switch controllers with explicit clicks. '
            'Status displays do not gate commands; responses come from the UR/driver.')
        self.banner.setStyleSheet('padding:10px;border-radius:4px;background:#e6eff9;color:#173d62;font-weight:bold' if self.mock else
                                  'padding:10px;border-radius:4px;background:#fff0d5;color:#724800;font-weight:bold')
        self.update_buttons()
        self.render_status()

    def update_buttons(self):
        busy=any(key!='status' for key in self.jobs)
        available=bool(self.selected())
        self.mode.setEnabled(not self.drivers and not busy)
        for key,button in self.buttons.items():
            allowed=not busy
            if key in ('cartesian','trajectory','rqt'):allowed=allowed and available
            if key in ('prepare','play'):allowed=allowed and not self.mock and available
            if key=='inactive':allowed=allowed and available
            button.setEnabled(allowed)

    def process(self,args,*,tag,finished=None):
        process=QtCore.QProcess(self)
        process.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.MergedChannels)
        process.setProperty('output','')
        output_file=self.session.process_log(tag,args)
        def read():
            chunk=bytes(process.readAllStandardOutput()).decode(errors='replace')
            if chunk:
                with output_file.open('a',encoding='utf-8') as stream:stream.write(chunk)
            process.setProperty('output',(process.property('output')+chunk)[-2_000_000:])
            if tag!='status' and chunk.strip():self.note(f'[{tag}] {chunk.strip()}')
        process.readyReadStandardOutput.connect(read)
        def done(code,status):
            read()
            with output_file.open('a',encoding='utf-8') as stream:stream.write(f'\nExit code: {code}; exit status: {status}\n')
            if finished:finished(code,process.property('output'))
            process.deleteLater()
        process.finished.connect(done)
        process.errorOccurred.connect(lambda e:self.note(f'{tag}: Process error {process.errorString()}'))
        process.start('/usr/bin/setsid',['--wait',*args]);return process

    def operation(self,kind,ids=None):
        ids=ids or self.selected()
        if not ids:return
        if kind in self.jobs:return
        mode='mock' if self.mock else 'hardware'
        report_feedback=self.manual_key==kind and self.manual_pending
        if report_feedback:
            self.manual_pending=False
            self.feedback.show_state('RUNNING',self.manual_title,'Selected arms: '+', '.join(LABELS[rid] for rid in ids))
        args=['ros2','run','match_ur_hardware','ur_operation','--inventory',str(self.inventory),
              '--arms',','.join(ids),'--mode',mode,kind]
        def done(code,output):
            self.jobs.pop(kind,None)
            ok=code==0;detail=self.error_detail(output) if code else 'Command completed. See the status or Log tab for details.'
            if kind=='status':
                try:
                    line=next(line for line in reversed(output.splitlines()) if line.startswith('{'))
                    data=json.loads(line)
                    if mode==('mock' if self.mock else 'hardware'):
                        for state in data.get('arms',{}).values():state['observed_at']=datetime.now().strftime('%H:%M:%S')
                        self.state.update(data.get('arms',{}));self.render_status()
                    detail='; '.join(f'{LABELS[rid]}: controller manager '+('responding' if state.get('driver_available') else 'NOT responding')
                                    for rid,state in data.get('arms',{}).items())
                except Exception as e:
                    ok=False;detail=f'Could not read status: {e}';self.note(detail)
            elif kind=='joints':
                try:
                    data=json.loads(next(line for line in reversed(output.splitlines()) if line.startswith('{')))
                    lines=['Received: '+datetime.now().strftime('%H:%M:%S')]
                    for rid,state in data.get('arms',{}).items():
                        lines.append('\n'+LABELS[rid])
                        if state.get('error'):lines.append(state['error'])
                        lines.extend(f'{name}: {value:.5f} rad  ({math.degrees(value):.2f}°)'
                                     for name,value in zip(state.get('names',[]),state.get('positions',[])))
                    self.joints.setPlainText('\n'.join(lines));self.tabs.setCurrentWidget(self.joints)
                except Exception as e:
                    ok=False;detail=f'Could not read joint angles: {e}';self.note(detail)
            else:
                self.note(f'{kind}: '+('completed' if code==0 else 'failed; see the log for details'))
            self.update_buttons()
            if kind=='cartesian':
                for rid in ids:
                    if rid in self.jog_dialogs:self.jog_dialogs[rid].controller_result(ok,detail)
            if report_feedback:self.action_result(kind,ok,detail)
        self.jobs[kind]=self.process(args,tag=kind,finished=done);self.update_buttons()

    def render_status(self):
        expanded={self.tree.topLevelItem(i).text(0):self.tree.topLevelItem(i).isExpanded()
                  for i in range(self.tree.topLevelItemCount())}
        self.tree.clear()
        for row,rid in enumerate(ARM_IDS):
            state=self.state.get(rid,{})
            answers={q['command']:q['answer'] for q in state.get('dashboard',{}).get('queries',[])}
            values=['ROS available' if state.get('driver_available') else 'Starting / no response' if rid in self.drivers else 'not started',
                    'Mock' if self.mock else answers.get('robotmode','—').removeprefix('Robotmode: ').strip(),
                    'Mock' if self.mock else answers.get('safetystatus','—').removeprefix('Safetystatus: ').strip(),
                    'Mock' if self.mock else answers.get('programState','—'),
                    '—' if self.mock else {True:'Yes',False:'No'}.get(state.get('dashboard',{}).get('remote_control'),'unknown')]
            for col,value in enumerate(values,2):self.table.item(row,col).setText(value)
            for col in range(7):self.table.item(row,col).setToolTip('Last query: '+state.get('observed_at','not yet'))
            if state.get('dashboard',{}).get('error'):self.table.item(row,2).setText('unreachable')
            parent=QtWidgets.QTreeWidgetItem([LABELS[rid],''])
            self.tree.addTopLevelItem(parent)
            for c in state.get('controllers',[]):parent.addChild(QtWidgets.QTreeWidgetItem([c['name'],c['state']]))
            parent.setExpanded(expanded.get(LABELS[rid],rid==ARM_IDS[0]))
        observed=max((s.get('observed_at','') for s in self.state.values()),default='')
        self.footer.setText(('Last selected-arm status query: '+observed if observed else 'No status data yet')+
                            ' · ROS domain 66 · software stop does not replace an emergency stop')
        if self.manual_key=='start' and self.feedback.phase=='RUNNING' and self.start_ids and all(self.state.get(rid,{}).get('driver_available') for rid in self.start_ids):
            self.action_result('start',True,'Controller managers are responding: '+', '.join(LABELS[rid] for rid in self.start_ids))

    def refresh(self):
        if not self.closing and not self.jobs:self.operation('status')

    def action(self,key):
        ids=self.selected()
        if not ids:
            self.note('Select at least one configured arm first.')
            self.action_result(key,False,'Select at least one configured arm first.');return
        if key=='status':self.operation('status');return
        if key=='jog':
            if len(ids)!=1:
                self.action_result('jog',False,'Select one arm for a jog window.');return
            rid=ids[0]
            if rid not in self.jog_dialogs:
                from .jog_dialog import JogDialog
                self.jog_dialogs[rid]=JogDialog(self,rid)
            self.jog_dialogs[rid].show();self.jog_dialogs[rid].raise_();self.jog_dialogs[rid].activateWindow()
            self.action_result('jog',True,'Jog window opened for '+LABELS[rid]+'. Hold an axis to command motion.');return
        if key in ('prepare','play','load','inactive','trajectory','cartesian','drivers_stop'):
            for dialog in self.jog_dialogs.values():dialog.stop('controller operation')
        if key=='start':
            self.start_ids=list(ids)
            self.feedback.show_state('RUNNING','Start drivers','Waiting for the selected controller managers to respond.')
            for rid in ids:
                if rid in self.drivers:continue
                if self.state.get(rid,{}).get('driver_available'):
                    self.note(f'{LABELS[rid]}: using the existing driver.');continue
                def done(code,output,rid=rid):
                    self.drivers.pop(rid,None);self.state.pop(rid,None)
                    self.note(f'{LABELS[rid]}: Driver stopped ({code})');self.update_buttons();self.render_status()
                    failed=code!=0 or 'controller manager exited' in output
                    self.action_result('start',not failed,self.error_detail(output) if failed else f'{LABELS[rid]}: driver stopped.')
                args=['ros2','launch','uwa_cell_control','arms.launch.py','inventory:='+str(self.inventory),
                      'arms:='+rid,'mode:='+('mock' if self.mock else 'hardware')]
                self.drivers[rid]=self.process(args,tag=rid,finished=done)
            self.update_buttons();self.render_status();return
        if key=='drivers_stop':
            for rid in ids:
                if rid in self.drivers:stop_owned_process(self.drivers[rid])
            self.action_result(key,True,'Owned driver processes stopped; external drivers were left running.')
            return
        if key=='rqt':
            p=self.process(['ros2','run','rqt_joint_trajectory_controller','rqt_joint_trajectory_controller'],tag='Joint control',
                           finished=lambda code,output:self.action_result('rqt',code==0,self.error_detail(output) if code else 'Joint control closed.'))
            p.started.connect(lambda:self.action_result('rqt',True,'Joint control process started.'))
            self.auxiliary.append(p);return
        self.operation(key)

    def stop_all(self):
        ids=sorted(set(self.drivers)|set(self.selected())|set(self.jog_dialogs))
        for dialog in self.jog_dialogs.values():dialog.stop('main STOP')
        if not ids:return
        for key,process in list(self.jobs.items()):
            stop_owned_process(process)
        self.jobs={}
        self.operation('stop',ids)

    def edit_inventory(self):
        ok=QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.inventory)))
        self.action_result('Open inventory',ok,str(self.inventory))

    def reload_inventory(self):
        if self.drivers or self.jobs:
            self.note('Stop owned drivers and operations before reloading the inventory.')
            self.action_result('Reload inventory',False,'Stop owned drivers and operations before reloading the inventory.');return
        try:
            self.profiles=load_profiles(self.inventory)
            for row,rid in enumerate(ARM_IDS):self.table.item(row,1).setText(self.profiles[rid]['ip'] or 'not configured')
            self.change_mode();self.note('Inventory reloaded.')
            self.action_result('Reload inventory',True,'Inventory reloaded.')
        except Exception as e:
            self.note(str(e));self.action_result('Reload inventory',False,str(e))

    def closeEvent(self,event):
        if self.export_worker is not None:
            self.close_after_export=True;event.ignore();return
        self.closing=True;self.timer.stop()
        for dialog in list(self.jog_dialogs.values()):dialog.close()
        for p in list(self.jobs.values()):stop_owned_process(p)
        for p in list(self.drivers.values())+self.auxiliary:stop_owned_process(p)
        event.accept()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    ws=Path(os.environ.get('UWA_WS',str(Path.home()/'UWA_ws')))
    parser.add_argument('--inventory',default=str(ws/'src/multi_arm_manipulation_UWA/config/hardware_inventory.yaml'))
    parser.add_argument('--arms',default='right_rear',help='Comma-separated initial arm selection')
    parser.add_argument('--mode',choices=['mock','hardware'],default='mock')
    parser.add_argument('--jog',action='store_true',help='Open the selected arm jog window without activating a controller')
    parser.add_argument('--start-drivers',action='store_true',help='Start selected local drivers; no power, brake or program commands')
    args=parser.parse_args()
    arms=args.arms.split(',')
    if not arms or not set(arms)<=set(ARM_IDS):parser.error('Unknown arm selection')
    os.environ['ROS_DOMAIN_ID']='66';os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE']='LOCALHOST'
    app=QtWidgets.QApplication([sys.argv[0]])
    app.setDesktopFileName('uwa-control')
    window=Window(args.inventory,arms=arms,mode=args.mode);window.show()
    if args.start_drivers:
        def start_drivers():
            window.acknowledge('start','Start drivers',window.buttons['start']);window.action('start')
        QtCore.QTimer.singleShot(300,start_drivers)
    if args.jog:QtCore.QTimer.singleShot(500,lambda:window.action('jog'))
    signal.signal(signal.SIGINT,lambda *unused:window.close())
    timer=QtCore.QTimer();timer.timeout.connect(lambda:None);timer.start(250)
    return app.exec()
