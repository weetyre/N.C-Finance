from PyQt5 import QtCore
from PyQt5.QtWidgets import QTabWidget

from .DyStockSelectStrategyRegressionResultWidget import *
from EventEngine.DyEvent import *


class DyStockSelectRegressionResultWidget(QTabWidget):

    signal = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self, eventEngine, paramWidget):
        super().__init__()

        self._eventEngine = eventEngine
        self._paramWidget = paramWidget

        self._newRegressionStrategyCls = None
        self._strategyWidgets = {}

        self._windows = [] # only for show
        
        self._registerEvent()

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._closeTab)

        self._initTabBarMenu()
    # 初始化表头右键菜单
    def _initTabBarMenu(self):
        """ 初始化表头右键菜单 """
        # 设置Tab右键菜单事件
        tabBar = self.tabBar()
        tabBar.setContextMenuPolicy(Qt.CustomContextMenu)
        tabBar.customContextMenuRequested.connect(self._showTabContextMenu)
        
        # 创建TabBar菜单
        self._tabBarMenu = QMenu(self)

        action = QAction('合并周期', self)
        action.triggered.connect(self._mergePeriodAct)
        self._tabBarMenu.addAction(action)

        action = QAction('描述统计', self)
        action.triggered.connect(self._describeAct)
        self._tabBarMenu.addAction(action)

        action = QAction('散布图矩阵', self)
        action.triggered.connect(self._scatterMatrixAct)
        self._tabBarMenu.addAction(action)

        self._tabBarMenu.addSeparator()

        # 初始化二级菜单
        self._probDistMenu = None
    # 显示上下文菜单
    def _showTabContextMenu(self, position):
        self._rightClickedTabIndex = self.tabBar().tabAt(position)# 获得右键索引

        # 如果二级菜单没有添加，动态添加二级菜单
        if self._probDistMenu is None:
            colNames = self.widget(self._rightClickedTabIndex).getNumberColNames()# 获取数字列名
            if colNames:
                self._probDistMenu = self._tabBarMenu.addMenu('概率分布')# 这是一个子菜单

                # 创建操作
                for name in colNames:
                    probDistAction = QAction(name, self)
                    probDistAction.triggered.connect(self._probDistAct)
                    probDistAction.setCheckable(True)

                    self._probDistMenu.addAction(probDistAction)

        self._tabBarMenu.popup(QCursor.pos())
    #  概率分布
    def _probDistAct(self):
        # get triggered action
        for action in self._probDistMenu.actions():
            if action.isChecked():
                action.setChecked(False)
                self.widget(self._rightClickedTabIndex).probDistAct(action.text())# 概率分布
                return
    #
    def _describeAct(self):
        self.widget(self._rightClickedTabIndex).describe()
    #
    def _mergePeriodAct(self):
        self.widget(self._rightClickedTabIndex).mergePeriod(self.tabText(self._rightClickedTabIndex))
    #
    def _scatterMatrixAct(self):
        self.widget(self._rightClickedTabIndex).scatterMatrix()
    # 获取回归的结果，主要是显示，每一个基准日结束之后，都会执行一遍
    def _stockSelectStrategyRegressionAckHandler(self, event):
        # unpack
        strategyCls = event.data['class']
        result = event.data['result']# 回归结果（单结果）
        period = event.data['period']
        day = event.data['day']
        if result is None: return

        tabName = strategyCls.chName

        # remove tab window's tabs if existing
        if self._newRegressionStrategyCls == strategyCls and tabName in self._strategyWidgets:
            self._strategyWidgets[tabName].removeAll()# 移除那个策略tab，为了重新加载

        # create new strategy result tab
        if tabName not in self._strategyWidgets:# 第一次的时候要初始化这个实例，第二次就不需要了
            widget = DyStockSelectStrategyRegressionResultWidget(self._eventEngine, strategyCls, self._paramWidget)
            self.addTab(widget, tabName)# 给当前tabName再加一个子tab

            # save
            self._strategyWidgets[tabName] = widget# 建立起对应的关系

        self._newRegressionStrategyCls = None# 之后就把他清空，供其他策略使用，并且确保不会执行existing 那个函数
        # 之后每次在这个widget 里添加结果就行
        self._strategyWidgets[tabName].append(period, day, result)

        self.parentWidget().raise_()
    # 注册事件
    def _registerEvent(self):
        self.signal.connect(self._stockSelectStrategyRegressionAckHandler) # 获取数据
        self._eventEngine.register(DyEventType.stockSelectStrategyRegressionAck, self.signal.emit)

        self._eventEngine.register(DyEventType.stockSelectStrategyRegressionReq, self._stockSelectStrategyRegressionReqHandler)# 回归请求
    # 关闭tab所进行的操作
    def _closeTab(self, index):
        tabName = self.tabText(index)
        self._strategyWidgets[tabName].close()

        del self._strategyWidgets[tabName]

        self.removeTab(index)
    # 回归请求，也就是确认一个新的回归类（这是一个同一个事件类，两个处理函数，这是其中一个，当然先执行这个）
    def _stockSelectStrategyRegressionReqHandler(self, event):
        self._newRegressionStrategyCls = event.data['class']# 新的回归策略类
    # 载入数据，重新恢复窗口
    def load(self, data, strategyCls):
        """
            @data: JSON data
        """
        className = data.get('class')
        if not className:
            return False

        if className != 'DyStockSelectStrategyRegressionResultWidget':
            return False

        window = DyStockSelectStrategyRegressionPeriodResultWidget(self._eventEngine, data['name'], strategyCls)
        window.rawSetColNames(data['data']['colNames'])
        window.rawAppend(data['data']['rows'], data['autoForegroundColName'])

        window.setWindowTitle('{0}{1}'.format(strategyCls.chName, data['name']))
        window.showMaximized()

        self._windows.append(window)

        return True

