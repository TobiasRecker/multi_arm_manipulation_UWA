"""Persistent, high-contrast action acknowledgement; colour is supplemental."""
import time
from python_qt_binding import QtCore,QtWidgets


class ActionFeedback(QtWidgets.QFrame):
    def __init__(self,parent=None):
        super().__init__(parent)
        layout=QtWidgets.QVBoxLayout(self);layout.setContentsMargins(12,8,12,8)
        self.heading=QtWidgets.QLabel();self.heading.setWordWrap(True)
        self.detail=QtWidgets.QLabel();self.detail.setWordWrap(True)
        self.heading.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.detail.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        layout.addWidget(self.heading);layout.addWidget(self.detail)
        self.progress=QtWidgets.QProgressBar();self.progress.setRange(0,0)
        self.progress.setMaximumHeight(8);layout.addWidget(self.progress)
        self.clock=QtCore.QTimer(self);self.clock.timeout.connect(self.tick);self.clock.start(250)
        self.phase='';self.message='';self.started=0.
        self.show_state('READY','Choose an action.','Button clicks and results appear here.')

    def show_state(self,phase,title,detail=''):
        colours={'READY':'#192b42','RECEIVED':'#123f85','RUNNING':'#583500',
                 'DONE':'#084623','FAILED':'#790c0c','INFO':'#192b42'}
        self.phase=phase;self.message=title;self.started=time.monotonic()
        self.full_detail=detail
        self.detail.setText(detail if len(detail)<=650 else detail[:600]+'… See the Log tab for full details.')
        self.detail.setToolTip(detail)
        self.progress.setVisible(phase=='RUNNING')
        self.setStyleSheet(f'QFrame {{background:{colours[phase]};border:3px solid #000;}} '
                          'QLabel {color:white;border:0;background:transparent;}')
        self.heading.setStyleSheet('font-size:17px;font-weight:bold;color:white;border:0;')
        self.tick()
        self.repaint()

    def tick(self):
        suffix=f' · {int(time.monotonic()-self.started)} s' if self.phase=='RUNNING' else ''
        self.heading.setText(f'{self.phase} · {self.message}{suffix}')
