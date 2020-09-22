from PyQt5.QtWidgets import QTabWidget

from .DyStockTradeBrokerAccountWidget import *
from ....DyStockTradeCommon import *

# 右下角账户窗口（这是一个基类，还要载入具体的broker，且登陆后才进行载入）
class DyStockTradeAccountWidget(QTabWidget):
    """ 股票交易账户窗口, 管理所有券商的账户窗口 """

    signalLogin = QtCore.pyqtSignal(type(DyEvent()))
    signalLogout = QtCore.pyqtSignal(type(DyEvent()))


    def __init__(self, eventEngine):
        super().__init__()

        self._eventEngine = eventEngine

        self._brokerAccountWidgets = {}

        self._registerEvent()
    # 注册时间
    def _registerEvent(self):
        self.signalLogin.connect(self._stockLoginHandler)
        self._eventEngine.register(DyEventType.stockLogin, self.signalLogin.emit)

        self.signalLogout.connect(self._stockLogoutHandler)
        self._eventEngine.register(DyEventType.stockLogout, self.signalLogout.emit)
    # 且登录后，创建券商股票交易窗口
    def _stockLoginHandler(self, event):
        broker = event.data['broker']

        # create broker account widget
        widget = DyStockTradeBrokerAccountWidget(self._eventEngine, broker)
        self.addTab(widget, DyStockTradeCommon.accountMap[broker])# 添加broker tab

        self._brokerAccountWidgets[broker] = widget
    # 登出事件
    def _stockLogoutHandler(self, event):
        broker = event.data['broker']

        widget = self._brokerAccountWidgets[broker]
        widget.close()# 把他拿出来，先关了，然后在移走

        self.removeTab(self.indexOf(widget))

        del self._brokerAccountWidgets[broker]
        