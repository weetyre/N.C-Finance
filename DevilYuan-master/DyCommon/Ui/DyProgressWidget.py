from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QLabel, QProgressBar
from PyQt5.Qt import QVBoxLayout


from EventEngine.DyEvent import *

#双进度条对话框
class DyProgressWidget(QWidget):
    signalSingle = QtCore.pyqtSignal(type(DyEvent()))
    signalTotal = QtCore.pyqtSignal(type(DyEvent()))
    #准备两个事件handler
    def __init__(self, eventEngine, parent=None):
        super().__init__(parent)
        self._eventEngine = eventEngine
        
        self._initUi()
        self._registerEvent()

    def _initUi(self):
        """初始化界面"""
        self.setWindowTitle('进度')

        labelTotal = QLabel('总体进度')
        labelSingle = QLabel('个体进度')
        #用的Pyqt5内置进度条类
        self._progressSingle = QProgressBar(self)
        self._progressTotal = QProgressBar(self)
        #垂直布局，加拉伸效果
        vbox = QVBoxLayout()
        vbox.addWidget(labelTotal)
        vbox.addWidget(self._progressTotal)
        vbox.addWidget(labelSingle)
        vbox.addWidget(self._progressSingle)
        vbox.addStretch()

        self.setLayout(vbox)

    def _updateProgressSingle(self, event):
        self._progressSingle.setValue(event.data)

    def _updateProgressTotal(self, event):
        self._progressTotal.setValue(event.data)

    def _registerEvent(self):
        """连接Signal（处理函数）"""
        self.signalSingle.connect(self._updateProgressSingle)
        self.signalTotal.connect(self._updateProgressTotal)
        """然后给注册给引擎 """
        self._eventEngine.register(DyEventType.progressSingle, self.signalSingle.emit)
        self._eventEngine.register(DyEventType.progressTotal, self.signalTotal.emit)

