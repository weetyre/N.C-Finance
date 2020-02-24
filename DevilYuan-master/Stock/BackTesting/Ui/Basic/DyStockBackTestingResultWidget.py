from PyQt5 import QtCore
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtGui import QCursor

from .Strategy.DyStockBackTestingStrategyResultWidget import *
from EventEngine.DyEvent import *
from DyCommon.DyCommon import *
from ....Data.Engine.DyStockDataEngine import *
from ....Data.Viewer.DyStockDataViewer import *

#显示回测结果的Dock（核心类，涉及引擎的启动）
class DyStockBackTestingResultWidget(QTabWidget):
    #这是重点，signal 激活函数
    reqSignal = QtCore.pyqtSignal(type(DyEvent()))
    ackSignal = QtCore.pyqtSignal(type(DyEvent()))
    newParamSignal = QtCore.pyqtSignal(type(DyEvent()))
    newPeriodSignal = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self, eventEngine):
        super().__init__()

        self._eventEngine = eventEngine

        self._strategyWidgets = {}
        self._windows = []
        #可以关闭TAB
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._closeTab)

        self._initTabBarMenu() # 初始化表头右键菜单

        self._initDataViewer()# 

        self._registerEvent()

    def _initTabBarMenu(self):
        """初始化表头右键菜单"""

        # 设置Tab右键菜单事件
        tabBar = self.tabBar()
        tabBar.setContextMenuPolicy(Qt.CustomContextMenu)
        tabBar.customContextMenuRequested.connect(self._showTabContextMenu)
        
        # 创建TabBar菜单
        self._tabBarMenu = QMenu(self) 

        # 创建操作
        #action = QAction('按盈亏升序排序', self)
        #action.triggered.connect(self._pnlRatioAscendingSortAct)
        #self._tabBarMenu.addAction(action)

        #action = QAction('按盈亏降序排序', self)
        #action.triggered.connect(self._pnlRatioDescendingSortAct)
        #self._tabBarMenu.addAction(action)

        action = QAction('参数组合统计总览', self)
        action.triggered.connect(self._paramGroupStatsOverviewAct)
        self._tabBarMenu.addAction(action)

    #涉及右键弹出的位置
    def _showTabContextMenu(self, position):
        self._rightClickedTabIndex = self.tabBar().tabAt(position)

        self._tabBarMenu.popup(QCursor.pos())
    #回测后的数据更新
    def _stockStrategyBackTestingAckHandler(self, event):
        # unpack
        ackData = event.data
        strategyCls = ackData.strategyCls

        tabName = strategyCls.chName
        self._strategyWidgets[tabName].update(ackData)
    #注册事件
    def _registerEvent(self):
        self.ackSignal.connect(self._stockStrategyBackTestingAckHandler)
        self._eventEngine.register(DyEventType.stockStrategyBackTestingAck, self.ackSignal.emit)

        self.reqSignal.connect(self._stockStrategyBackTestingReqHandler)
        self._eventEngine.register(DyEventType.stockStrategyBackTestingReq, self.reqSignal.emit)

        self.newParamSignal.connect(self._newParamHandler)
        self._eventEngine.register(DyEventType.newStockStrategyBackTestingParam, self.newParamSignal.emit)

        self.newPeriodSignal.connect(self._newPeriodHandler)
        self._eventEngine.register(DyEventType.newStockStrategyBackTestingPeriod, self.newPeriodSignal.emit)
    #关闭了这个TAB后需要处理的
    def _closeTab(self, index):
        tabName = self.tabText(index)

        del self._strategyWidgets[tabName]

        self.removeTab(index)
    #
    def _stockStrategyBackTestingReqHandler(self, event):
        """ 开始一个策略的回测 """
        strategyCls = event.data.strategyCls

        tabName = strategyCls.chName

        # 是不是重新开始一个策略的回测
        if tabName in self._strategyWidgets:
            self._strategyWidgets[tabName].removeAll()# 移除所有参数
        else:
            widget = DyStockBackTestingStrategyResultWidget(strategyCls, self._eventEngine, self._dataEngine, self._dataViewer)
            self.addTab(widget, tabName)

            # save
            self._strategyWidgets[tabName] = widget
        #
        self.parentWidget().raise_()
    #初始化相应的引擎
    def _initDataViewer(self):
        errorInfo = DyErrorInfo(self._eventEngine)
        self._dataEngine = DyStockDataEngine(self._eventEngine, errorInfo, False)
        self._dataViewer = DyStockDataViewer(self._dataEngine, errorInfo)

    #新的参数
    def _newParamHandler(self, event):
        strategyCls = event.data['class']
        tabName = strategyCls.chName

        self._strategyWidgets[tabName].newParam(event)
    #新的周期
    def _newPeriodHandler(self, event):
        strategyCls = event.data['class']
        tabName = strategyCls.chName

        self._strategyWidgets[tabName].newPeriod(event)
    #
    def _pnlRatioAscendingSortAct(self):
        self.widget(self._rightClickedTabIndex).sort(True)
    #
    def _pnlRatioDescendingSortAct(self):
        self.widget(self._rightClickedTabIndex).sort(False)
    #
    def _paramGroupStatsOverviewAct(self):
        self.widget(self._rightClickedTabIndex).paramGroupStatsOverview()
    #载入结果数据
    def loadDeals(self, data, strategyCls):
        """
            载入回测成交数据
            @data: JSON data
        """
        className = data.get('class')
        if not className:
            return False

        if className != 'DyStockBackTestingStrategyResultDealsWidget':
            return False

        #显示结果
        window = DyStockBackTestingStrategyResultDealsWidget(self._eventEngine, data['name'], strategyCls)
        window.setColNames(data['data']['colNames'])
        window.fastAppendRows(data['data']['rows'], data['autoForegroundColName'])

        window.setAllItemsForeground()

        window.setWindowTitle('成交明细-{0}{1}'.format(strategyCls.chName, data['name']))
        window.showMaximized()

        self._windows.append(window)

        return True