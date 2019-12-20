from PyQt5 import QtCore
from PyQt5.QtGui import QColor

from .DyTableWidget import *
from EventEngine.DyEvent import *

#log表格相关逻辑
class DyLogWidget(DyTableWidget):
    #准备发送事件类信号，注意语法
    signal = QtCore.pyqtSignal(type(DyEvent()))
    #日志表格的header
    header = ['时间','类型(错误:0,警告:0)','描述']

    def __init__(self, eventEngine=None):
        super().__init__(None, True, True)
        #log事件必须用到引擎来派发，来注册
        self._eventEngine = eventEngine

        self._errorCount = 0
        self._warningCount = 0

        self.setColNames(self.header)

        self._registerEvent()
    #根据消息的类型，来显示不同的文字信息
    def _setRowForeground(self, row, data):
        if data.type == data.ind:
            self.setRowForeground(row, Qt.darkGreen)

        elif data.type == data.ind1:
            self.setRowForeground(row, QColor("#4169E1"))

        elif data.type == data.ind2:
            self.setRowForeground(row, QColor("#C71585"))
        #有错误或者警告，计数器加1
        elif data.type == data.error:
            self._errorCount += 1
            self.setRowForeground(row, Qt.red)

        elif data.type == data.warning:
            self._warningCount += 1
            self.setRowForeground(row, QColor("#FF6100"))
    
    #每来一个事件执行一次这个函数
    def _logHandler(self, event):
        data = event.data
        #下面两个是新的参数，采用后跟新的逻辑，也就是先保存了，然后最后面的函数数目就不对等，之后就会更改header第二列
        savedErrorCount = self._errorCount
        savedWarningCount = self._warningCount

        self.setSortingEnabled(False)

        row = self.appendRow([data.time, data.type, data.description], disableSorting=False)

        self._setRowForeground(row, data)

        self.setSortingEnabled(True)
        # 如果有错误或者警告更改数目
        # check if need to change 类型 header name
        if self._errorCount != savedErrorCount or self._warningCount != savedWarningCount:
            self.setColName(1, '类型(错误:{0},警告:{1})'.format(self._errorCount, self._warningCount))

    def _registerEvent(self):
        """ 注册GUI更新相关的事件监听 """

        if self._eventEngine is None: return
        #通过指针函数调用，自动传入event参数，和刚开始对应，从而输入Event实例。
        self.signal.connect(self._logHandler)
        self._eventEngine.register(DyEventType.log, self.signal.emit)
        #调用函数先更新UI，然后注册（也就是放入事件引擎的queue,注意handler = emit 相当于一个指针，指向单独事件。）
    def append(self, logData):
        rows = [[data.time, data.type, data.description] for data in logData]#循环添加
        self.fastAppendRows(rows)
        #先添加，然后改变前景色，最后改变列的标题。
        for row, data in enumerate(logData):
            self._setRowForeground(row, data)

        self.setColName(1, '类型(错误:{0},警告:{1})'.format(self._errorCount, self._warningCount))
