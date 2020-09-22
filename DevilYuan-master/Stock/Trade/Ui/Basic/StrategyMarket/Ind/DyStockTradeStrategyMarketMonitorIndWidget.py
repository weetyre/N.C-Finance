from PyQt5 import QtCore
from PyQt5.QtWidgets import QTabWidget

from .DyStockTradeStrategyMarketMonitorOpWidget import *
from .DyStockTradeStrategyMarketMonitorSignalDetailsWidget import *
from .....DyStockStrategyBase import *
from .Account.DyStockTradeStrategyAccountWidget import *

# 股票策略实时指示窗口，也就是那个指示窗口
class DyStockTradeStrategyMarketMonitorIndWidget(QTabWidget):
    """
        股票策略实时指示窗口：
            操作窗口
            信号明细窗口
            策略实盘账户窗口 - 动态创建，只在策略绑定实盘账户时创建。

        由于此窗口在启动策略时就会创建，所以由它负责账户窗口的动态创建和对应的账户相关的更新事件。
        这样不会导致异步时丢失event的处理。
    """
    changeStockCtaStrategyStateSignal = QtCore.pyqtSignal(type(DyEvent())) # For creating or deleting Account Widget dynamically

    # 策略账户相关事件
    stockStrategyEntrustsUpdateSignal = QtCore.pyqtSignal(type(DyEvent()))
    stockStrategyDealsUpdateSignal = QtCore.pyqtSignal(type(DyEvent()))
    stockStrategyPosUpdateSignal = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self, eventEngine, strategyCls, strategyState):
        super().__init__()

        self._eventEngine = eventEngine
        self._strategyCls = strategyCls
        self._strategyState = strategyState

        self._initUi()

        self._registerEvent()
    # 指示窗口又有三个小窗口
    def _initUi(self):
        self._opWidget = DyStockTradeStrategyMarketMonitorOpWidget(self._strategyCls)
        self.addTab(self._opWidget, '操作')

        self._signalDetailsWidget = DyStockTradeStrategyMarketMonitorSignalDetailsWidget(self._strategyCls)
        self.addTab(self._signalDetailsWidget, '信号明细')

        if self._strategyState.isState(DyStockStrategyState.running) and self._strategyCls.broker is not None:
            self._accountWidget = DyStockTradeStrategyAccountWidget(self._eventEngine, self._strategyCls)
            self.addTab(self._accountWidget, '账户')
        else:
            self._accountWidget = None
    # 更新对应的数据（操作，和信号明细）
    def update(self, data):
        """
            操作和信号明细的数据更新
            @data: {'op': [[data]], 'signalDetails': [[data]]}
        """
        if 'op' in data:# 操作
            self._opWidget.update(data['op'])

        if 'signalDetails' in data:# 信号明细
            self._signalDetailsWidget.update(data['signalDetails'])
    # 关闭事件
    def closeEvent(self, event):
        self._opWidget.close()
        self._signalDetailsWidget.close()
        if self._accountWidget:
            self._accountWidget.close()

        self._unregisterEvent()

        return super().closeEvent(event)
    # 持仓，成交，委托，以及策略运行状态改变
    def _registerEvent(self):
        self.changeStockCtaStrategyStateSignal.connect(self._changeStockCtaStrategyStateHandler)
        self._eventEngine.register(DyEventType.changeStockCtaStrategyState, self._changeStockCtaStrategyStateSignalEmitWrapper)

        self.stockStrategyEntrustsUpdateSignal.connect(self._stockStrategyEntrustsUpdateHandler)
        self._eventEngine.register(DyEventType.stockStrategyEntrustsUpdate + self._strategyCls.name, self._stockStrategyEntrustsUpdateSignalEmitWrapper)

        self.stockStrategyDealsUpdateSignal.connect(self._stockStrategyDealsUpdateHandler)
        self._eventEngine.register(DyEventType.stockStrategyDealsUpdate + self._strategyCls.name, self._stockStrategyDealsUpdateSignalEmitWrapper)

        self.stockStrategyPosUpdateSignal.connect(self._stockStrategyPosUpdateHandler)
        self._eventEngine.register(DyEventType.stockStrategyPosUpdate + self._strategyCls.name, self._stockStrategyPosUpdateSignalEmitWrapper)
    # 对应解除注册
    def _unregisterEvent(self):
        self.changeStockCtaStrategyStateSignal.disconnect(self._changeStockCtaStrategyStateHandler)
        self._eventEngine.unregister(DyEventType.changeStockCtaStrategyState, self._changeStockCtaStrategyStateSignalEmitWrapper)

        self.stockStrategyEntrustsUpdateSignal.disconnect(self._stockStrategyEntrustsUpdateHandler)
        self._eventEngine.unregister(DyEventType.stockStrategyEntrustsUpdate + self._strategyCls.name, self._stockStrategyEntrustsUpdateSignalEmitWrapper)

        self.stockStrategyDealsUpdateSignal.disconnect(self._stockStrategyDealsUpdateHandler)
        self._eventEngine.unregister(DyEventType.stockStrategyDealsUpdate + self._strategyCls.name, self._stockStrategyDealsUpdateSignalEmitWrapper)

        self.stockStrategyPosUpdateSignal.disconnect(self._stockStrategyPosUpdateHandler)
        self._eventEngine.unregister(DyEventType.stockStrategyPosUpdate + self._strategyCls.name, self._stockStrategyPosUpdateSignalEmitWrapper)
    #
    def _changeStockCtaStrategyStateSignalEmitWrapper(self, event):
        """ !!!Note: The value of signal.emit will always be changed each time you getting.
        """
        self.changeStockCtaStrategyStateSignal.emit(event)
    # 股票委托更新
    def _stockStrategyEntrustsUpdateSignalEmitWrapper(self, event):
        """ !!!Note: The value of signal.emit will always be changed each time you getting.
        """
        self.stockStrategyEntrustsUpdateSignal.emit(event)
    #
    def _stockStrategyDealsUpdateSignalEmitWrapper(self, event):
        """ !!!Note: The value of signal.emit will always be changed each time you getting.
        """
        self.stockStrategyDealsUpdateSignal.emit(event)
    #
    def _stockStrategyPosUpdateSignalEmitWrapper(self, event):
        """ !!!Note: The value of signal.emit will always be changed each time you getting.
        """
        self.stockStrategyPosUpdateSignal.emit(event)
    # 更改策略运行状态后的操作
    def _changeStockCtaStrategyStateHandler(self, event):
        strategyCls = event.data['class']
        strategyState = event.data['state']

        if strategyCls != self._strategyCls:# 不是一个策略，不处理
            return
        # 如果在运行，且没创建那个tab，那创建，如果已有就不创建
        if strategyState.isState(DyStockStrategyState.running) and self._accountWidget is None and strategyCls.broker is not None:
            self._accountWidget = DyStockTradeStrategyAccountWidget(self._eventEngine, self._strategyCls)
            self.addTab(self._accountWidget, '账户')
        # 如果不是运行状态且，已经有，那就删除
        elif not strategyState.isState(DyStockStrategyState.running) and self._accountWidget is not None:
            self._accountWidget.close()
            self.removeTab(self.indexOf(self._accountWidget))

            self._accountWidget = None

        self._strategyState = strategyState
    # 股票委托更新响应
    def _stockStrategyEntrustsUpdateHandler(self, event):
        if self._accountWidget:
            self._accountWidget.updateEntrusts(event)
    # 成交更新
    def _stockStrategyDealsUpdateHandler(self, event):
        if self._accountWidget:
            self._accountWidget.updateDeals(event)
    # 持仓更新UI
    def _stockStrategyPosUpdateHandler(self, event):
        if self._accountWidget:
            self._accountWidget.updatePos(event)# 更新UI

