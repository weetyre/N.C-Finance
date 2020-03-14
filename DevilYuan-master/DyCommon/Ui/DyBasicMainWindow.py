from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow, QDockWidget, QLabel

from EventEngine.DyEvent import *
from DyCommon.DyCommon import *
from Stock.Common.DyStockCommon import *

#主要控制按钮的状态，防止互斥操作
class DyBasicMainWindow(QMainWindow):

    name = 'DyBasicMainWindow'

    signalStopAck = QtCore.pyqtSignal(type(DyEvent()))
    signalFinish = QtCore.pyqtSignal(type(DyEvent()))
    signalFail = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self, eventEngine, info, parent=None, type='stock'):
        super().__init__(parent)
        
        self._info = info
        self.__type = type

        self._mutexActions = []
        self._runningAction = None
        self._runningActionText = None
        self._runningActionCount = 0

        if eventEngine is not None:
            self.__registerEvent(eventEngine)

        self.__initStatusBar()
    #初始化状态栏
    def __initStatusBar(self):
        if self.__type == 'stock':
            text = '股票历史日线数据源:{}'.format(','.join(DyStockCommon.defaultHistDaysDataSource))
            label = QLabel(text)
            self.statusBar().addPermanentWidget(label)
    #添加互斥操作
    def _addMutexAction(self, action):
        if action not in self._mutexActions:
            self._mutexActions.append(action)
    #开始运行互斥操作
    def _startRunningMutexAction(self, action, count=1):
        """
            @count: 并行运行操作的个数。也就是说当所有的操作都结束时，才能使能Action。
                    操作结束的种类：
                            失败
                            成功
                            停止
                    例子：
                        一键更新股票数据，包含2个独立并行操作，日线数据和历史分笔。
        """
        self._runningAction = action # 例如 ：一键更新股票数据
        self._runningActionText = action.text() # 一键更新股票数据
        self._runningActionCount = count # 2
        # 开始运行操作后，立马变为停止
        action.setText('停止')# 这是界面的那个停止按钮，action 是那一个按钮

        for action in self._mutexActions:
            if action != self._runningAction:
                action.setDisabled(True)# 其他按钮先不能点击，先确保这个action 运行完毕
    # 中止运行的互斥操作
    def _endRunningMutexAction(self):
        """ called once finish, fail or stopAck event received """
        if self._runningAction is None: return False

        self._runningActionCount -= 1

        # all ended
        if self._runningActionCount == 0:
            self._runningAction.setText(self._runningActionText)# 恢复原来按钮的文字

            self._runningAction = None
            self._runningActionText = None
            self._runningActionCount = 0

            for action in self._mutexActions:
                action.setEnabled(True)# 其他互斥操作已经可以点击

            return True

        return False
    #停止正在运行的互斥操作，让那个停止按钮无法点击
    def _stopRunningMutexAction(self):
        self._runningAction.setDisabled(True)
    # 所有的事件停止都由这个操作
    def _endHandler(self, event):
        """
            if program not processed carefully, event finish and stopAck might comming both.
            In that case, always ignore last one.
        """
        if event.type == DyEventType.finish:
            if self._endRunningMutexAction():
                self._info.print('成功完成', DyLogData.ind)

        elif event.type == DyEventType.fail:
            if self._endRunningMutexAction():
                self._info.print('失败', DyLogData.error)

        elif event.type == DyEventType.stopAck:
            if self._endRunningMutexAction():
                self._info.print('已经停止', DyLogData.ind)

    def __registerEvent(self, eventEngine):
        """注册GUI更新相关的事件监听"""
        self.signalStopAck.connect(self._endHandler)
        self.signalFinish.connect(self._endHandler)
        self.signalFail.connect(self._endHandler)

        eventEngine.register(DyEventType.stopAck, self.signalStopAck.emit)
        eventEngine.register(DyEventType.finish, self.signalFinish.emit)
        eventEngine.register(DyEventType.fail, self.signalFail.emit)
    # 保存窗口设置
    def _saveWindowSettings(self):
        """保存窗口设置"""
        settings = QtCore.QSettings('DevilYuan', 'DevilYuanQuant')
        settings.setValue(self.name + 'State', self.saveState())
        settings.setValue(self.name + 'Geometry', self.saveGeometry())
    #先载入后保存
    def _loadWindowSettings(self):
        """载入窗口设置"""
        settings = QtCore.QSettings('DevilYuan', 'DevilYuanQuant')
        try:
            ret = self.restoreState(settings.value(self.name + 'State')) # 这是用的父类的方法进行恢复
            ret = self.restoreGeometry(settings.value(self.name + 'Geometry'))    
        except Exception as ex:
            pass
    #关闭事件，保存窗口设置再关闭
    def closeEvent(self, event):
        self._saveWindowSettings()

        return super().closeEvent(event)
    # 创建停靠组件
    def _createDock(self, widgetClass, widgetName, widgetArea, *param):
        """创建停靠组件"""

        widget = widgetClass(*param)#根据自己写的特定类自定义组件，参数是继承参数

        dock = QDockWidget(widgetName, self)
        dock.setWidget(widget)
        dock.setObjectName(widgetName)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures) # 没有什么额外的特征
        self.addDockWidget(widgetArea, dock)
        return widget, dock # dock才是QT本身的
