from EventEngine.DyEvent import *
from ..DyStockTradeCommon import *
from .YhNew.YhTrader import YhTrader
from .Ths.ThsTrader import ThsTrader
from .Simu.SimuTrader import *

# 券商交易接口引擎
class DyStockTradeBrokerEngine(object):
    """ 券商交易接口引擎 """
    # 不同的券商的映射
    traderMap = {
                 'yh': YhTrader,
                 'ths': ThsTrader,

                 'simu1': SimuTrader1,# 都是具体的类
                 'simu2': SimuTrader2,
                 'simu3': SimuTrader3,
                 'simu4': SimuTrader4,
                 'simu5': SimuTrader5,
                 'simu6': SimuTrader6,
                 'simu7': SimuTrader7,
                 'simu8': SimuTrader8,
                 'simu9': SimuTrader9,
                 }

    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._traders = {}

        self._registerEvent()
    # 注册登录，登出的事件,有CTA策略启动登录，登出
    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockLogin, self._stockLoginHandler, DyStockTradeEventHandType.brokerEngine)
        self._eventEngine.register(DyEventType.stockLogout, self._stockLogoutHandler, DyStockTradeEventHandType.brokerEngine)
    # 登录处理函数，两个函数映射，还要创建交易窗口
    def _stockLoginHandler(self, event):
        broker = event.data['broker']# 比如simu2

        # create trader instance
        trader = self.traderMap[broker](self._eventEngine, self._info)# trader实例

        # login
        trader.login()

        # sync pos
        trader.syncPos()

        # update account
        trader.updateAccount()

        self._traders[broker] = trader# broker 加具体的实例
    # 券商登出（有两个函数 还有一个把界面拿出来，先关了，然后在移走）
    def _stockLogoutHandler(self, event):
        broker = event.data['broker']
        oneKeyHangUp = True if event.data.get('oneKeyHangUp') else False # 是否是一键挂机导致的交易接口退出

        trader = self._traders[broker]

        trader.logout(oneKeyHangUp)

        del self._traders[broker]# 然后把这个实例删除了