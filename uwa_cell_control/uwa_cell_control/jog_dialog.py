"""MuR-style Cartesian jogging without lift/mobile-host controls."""
from functools import partial
from python_qt_binding import QtCore,QtWidgets
from match_mur_gui.jog_commands import cartesian_twist
from match_ur_hardware.jog import JogTransport
from match_ur_hardware.profiles import CARTESIAN


class JogDialog(QtWidgets.QDialog):
    def __init__(self,main,rid,*,transport_factory=None):
        super().__init__(main)
        self.main=main;self.rid=rid;self.profile=main.profiles[rid]
        self.active=[0.]*6;self.zero_ticks=0;self.closed=False
        self.transport=(transport_factory or JogTransport)(self.profile)
        self.setWindowTitle('UWA Cartesian jog · '+rid);self.resize(660,480)
        layout=QtWidgets.QVBoxLayout(self)
        mode='MOCK' if main.mock else 'HARDWARE'
        compliance='ON' if self.profile['compliance_enabled'] else 'OFF'
        header=QtWidgets.QLabel(f'{mode} · {rid}\nBase frame: {self.profile["prefix"]}base_link\n'
            f'Compliance preset: {compliance} · applied by Enable jog controller')
        header.setStyleSheet('background:#172e4d;color:white;padding:12px;font-size:15px;font-weight:bold')
        layout.addWidget(header)
        speed=QtWidgets.QHBoxLayout();self.mode=QtWidgets.QComboBox()
        self.mode.addItems(['Translation','Rotation']);self.mode.currentIndexChanged.connect(lambda unused:self.stop('mode changed'))
        speed.addWidget(self.mode)
        self.linear_speed=QtWidgets.QDoubleSpinBox();self.linear_speed.setRange(.001,.03)
        self.linear_speed.setDecimals(3);self.linear_speed.setSingleStep(.001);self.linear_speed.setValue(.01)
        self.angular_speed=QtWidgets.QDoubleSpinBox();self.angular_speed.setRange(.01,.1)
        self.angular_speed.setDecimals(3);self.angular_speed.setSingleStep(.01);self.angular_speed.setValue(.1)
        speed.addWidget(QtWidgets.QLabel('m/s'));speed.addWidget(self.linear_speed)
        speed.addWidget(QtWidgets.QLabel('rad/s'));speed.addWidget(self.angular_speed);layout.addLayout(speed)
        grid=QtWidgets.QGridLayout();layout.addLayout(grid);self.axis_buttons={}
        for label,row,col,vector in [('Y+',0,1,[0,1,0]),('X-',1,0,[-1,0,0]),
                ('X+',1,2,[1,0,0]),('Y-',2,1,[0,-1,0]),('Z+',0,3,[0,0,1]),('Z-',2,3,[0,0,-1])]:
            button=QtWidgets.QPushButton(label);button.setMinimumHeight(58)
            button.setStyleSheet('QPushButton {background:#ecf1f7;color:#111;border:2px solid #172e4d;font-size:17px;font-weight:bold;}'
                                'QPushButton:pressed {background:#123f85;color:white;border:4px solid black;}')
            button.pressed.connect(partial(self.start,vector));button.released.connect(lambda:self.stop('released'))
            grid.addWidget(button,row,col);self.axis_buttons[label]=button
        self.stop_button=QtWidgets.QPushButton('STOP JOG');self.stop_button.setMinimumHeight(58)
        self.stop_button.setStyleSheet('background:#8a0909;color:white;border:3px solid #280000;font-weight:bold;font-size:17px')
        self.stop_button.clicked.connect(lambda:self.stop('STOP JOG'));grid.addWidget(self.stop_button,1,1)
        self.motion=QtWidgets.QLabel('IDLE · hold an axis button or key to jog')
        self.motion.setWordWrap(True);layout.addWidget(self.motion);self.show_motion(False,'IDLE · hold an axis button or key to jog')
        self.enable=QtWidgets.QPushButton('Enable jog controller')
        self.enable.setMinimumHeight(42)
        self.enable.setToolTip('Recreate the existing MATCH controller with the chosen compliance preset, then activate it. No power-on or program start.')
        self.enable.clicked.connect(self.enable_controller);layout.addWidget(self.enable)
        self.status=QtWidgets.QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        hint=QtWidgets.QLabel('Hold to jog. Release / Space / focus loss stops. M switches translation/rotation.\n'
            'Arrow keys: X/Y · PageUp/PageDown: Z · rates are in the robot base frame.\n'
            'Controller/program state is informational; the UR/driver decides which commands it accepts.')
        hint.setWordWrap(True);layout.addWidget(hint)
        self.timer=QtCore.QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(50)

    def show_motion(self,moving,text):
        self.motion.setText(text)
        self.motion.setStyleSheet('padding:10px;color:white;border:3px solid black;font-size:16px;font-weight:bold;'
                                 'background:'+('#123f85' if moving else '#172e4d'))
        self.motion.repaint()

    def start(self,vector):
        if self.closed:return
        mode='translation' if self.mode.currentIndex()==0 else 'rotation'
        self.active=cartesian_twist(vector,mode,self.linear_speed.value(),self.angular_speed.value())
        self.zero_ticks=0;self.transport.publish(self.active)
        text=f'JOGGING · {mode} · '+str(self.active)
        self.show_motion(True,text);self.main.note(f'{self.rid}: {text}')

    def stop(self,reason='released'):
        if self.closed:return
        if not any(self.active) and not self.zero_ticks:return
        self.active=[0.]*6;self.zero_ticks=3
        self.transport.publish(self.active)
        self.show_motion(False,'STOPPED · '+reason);self.main.note(f'{self.rid}: jog stopped · {reason}')

    def tick(self):
        if self.closed:return
        self.transport.spin()
        if any(self.active):self.transport.publish(self.active)
        elif self.zero_ticks:
            self.transport.publish(self.active);self.zero_ticks-=1
        controllers=self.main.state.get(self.rid,{}).get('controllers',[])
        state=next((c['state'] for c in controllers if c['name']==CARTESIAN),'not reported yet')
        self.status.setText(f'Controller: {state} · command subscribers: {self.transport.subscribers()}\n'
            f'UR External Control running: {self.transport.program_running}')

    def enable_controller(self):
        self.stop('controller change')
        self.show_motion(False,'ENABLING · applying the compliance preset…')
        self.main.acknowledge('cartesian','Enable jog controller',self.enable)
        self.main.operation('cartesian',[self.rid])

    def controller_result(self,ok,detail):
        self.show_motion(False,('CONTROLLER READY · ' if ok else 'CONTROLLER FAILED · ')+detail[:500])
        if not ok:self.motion.setStyleSheet('background:#790c0c;color:white;border:3px solid black;padding:10px;font-weight:bold')

    def keyPressEvent(self,event):
        if event.isAutoRepeat():event.accept();return
        key=event.key();keys=QtCore.Qt.Key
        mapping={keys.Key_Left:[-1,0,0],keys.Key_Right:[1,0,0],keys.Key_Up:[0,1,0],
            keys.Key_Down:[0,-1,0],keys.Key_PageUp:[0,0,1],keys.Key_PageDown:[0,0,-1]}
        if key in mapping:self.start(mapping[key]);event.accept();return
        if key in (keys.Key_Space,keys.Key_Period):self.stop('keyboard stop');event.accept();return
        if key==keys.Key_M:self.mode.setCurrentIndex(1-self.mode.currentIndex());event.accept();return
        super().keyPressEvent(event)

    def keyReleaseEvent(self,event):
        if event.isAutoRepeat():event.accept();return
        if event.key() in (QtCore.Qt.Key.Key_Left,QtCore.Qt.Key.Key_Right,QtCore.Qt.Key.Key_Up,
                          QtCore.Qt.Key.Key_Down,QtCore.Qt.Key.Key_PageUp,QtCore.Qt.Key.Key_PageDown):
            self.stop('key released');event.accept();return
        super().keyReleaseEvent(event)

    def event(self,event):
        if event.type() in (QtCore.QEvent.Type.WindowDeactivate,QtCore.QEvent.Type.Hide) and hasattr(self,'active'):
            self.stop('window inactive')
        return super().event(event)

    def snapshot(self):
        return {'arm':self.rid,'base_frame':self.profile['prefix']+'base_link','command':self.active,
                'mode':self.mode.currentText(),'compliance_preset':self.profile['compliance_enabled']}

    def closeEvent(self,event):
        if not self.closed:
            self.stop('dialog closed');self.timer.stop();self.transport.close();self.closed=True
            self.main.jog_dialogs.pop(self.rid,None)
        super().closeEvent(event)
