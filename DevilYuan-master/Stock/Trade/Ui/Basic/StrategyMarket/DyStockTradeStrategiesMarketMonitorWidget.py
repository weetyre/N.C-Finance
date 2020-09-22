from PyQt5 import QtCore
from PyQt5.QtWidgets import QTabWidget

from EventEngine.DyEvent import *
from DyCommon.Ui.DyTableWidget import *
from .DyStockTradeStrategyMarketMonitorWidget import *
from .Other.DyStockTradeStrategyBuyDlg import *
from .Other.DyStockTradeStrategySellDlg import *

# 策略行情窗口，或者是实时监控窗口 策略行情窗口(里面还要内陷，一个承载（数据，指示）的窗口)
class DyStockTradeStrategiesMarketMonitorWidget(QTabWidget):
    """
        所有策略的实时监控窗口
    """
    signalStartStockCtaStrategy = QtCore.pyqtSignal(type(DyEvent()))
    signalStopStockCtaStrategy = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self, eventEngine):
        super().__init__()

        self._eventEngine = eventEngine

        self._strategyMarketMonitorWidgets = {} # {strategy name: (widget instance, strategyCls)}

        self._initTabBarMenu()

        self._registerEvent()
    # 初始化Tab右键菜单
    def _initTabBarMenu(self):
        """ 初始化表头右键菜单 """
        # 设置Tab右键菜单事件
        tabBar = self.tabBar()
        tabBar.setContextMenuPolicy(Qt.CustomContextMenu)# 还是自定义的菜单
        tabBar.customContextMenuRequested.connect(self._showTabContextMenu)

        # 创建TabBar菜单
        self._tabBarMenu = QMenu(self)
        
        action = QAction('买入...', self)
        action.triggered.connect(self._buyAct)
        self._tabBarMenu.addAction(action)

        action = QAction('卖出...', self)
        action.triggered.connect(self._sellAct)
        self._tabBarMenu.addAction(action)
    # 自定义菜单的显示规则
    def _showTabContextMenu(self, position):
        self._rightClickedTabIndex = self.tabBar().tabAt(position)

        self._tabBarMenu.popup(QCursor.pos())
    # 买入
    def _buyAct(self):
        tabText = self.tabText(self._rightClickedTabIndex)#获取策略名

        strategyCls = self._strategyMarketMonitorWidgets[tabText][1]# 获取策略类

        DyStockTradeStrategyBuyDlg(self._eventEngine, strategyCls).exec_()
    # 卖出
    def _sellAct(self):
        tabText = self.tabText(self._rightClickedTabIndex)

        strategyCls = self._strategyMarketMonitorWidgets[tabText][1]

        DyStockTradeStrategySellDlg(self._eventEngine, strategyCls).exec_()
    # 开始策略，添加数据tab
    def _startStockCtaStrategyHandler(self, event):
        strategyCls = event.data['class']
        strategyState = event.data['state']

        # 添加策略行情窗口到Tab窗口
        widget = DyStockTradeStrategyMarketMonitorWidget(self._eventEngine, strategyCls, strategyState)
        self.addTab(widget, strategyCls.chName)# tab 加tab，策略开始才会真正的显示

        # save
        self._strategyMarketMonitorWidgets[strategyCls.chName] = (widget, strategyCls)
    # 关闭子TAB
    def _stopStockCtaStrategyHandler(self, event):
        strategyCls = event.data['class']

        widget = self._strategyMarketMonitorWidgets[strategyCls.chName][0]
        widget.close()

        self.removeTab(self.indexOf(widget))

        del self._strategyMarketMonitorWidgets[strategyCls.chName]

    def _registerEvent(self):
        self.signalStartStockCtaStrategy.connect(self._startStockCtaStrategyHandler)
        self._eventEngine.register(DyEventType.startStockCtaStrategy, self.signalStartStockCtaStrategy.emit)

        self.signalStopStockCtaStrategy.connect(self._stopStockCtaStrategyHandler)
        self._eventEngine.register(DyEventType.stopStockCtaStrategy, self.signalStopStockCtaStrategy.emit)


