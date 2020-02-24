class DyStockStopMode(object):
    #股票停止模式
    def __init__(self, accountManager):
        self._accountManager = accountManager
    # 子类改写
    def onOpen(self, date):
        return True

    def onTicks(self, ticks):
        pass

    def onBars(self, bars):
        pass

    def setAccountManager(self, accountManager):
        self._accountManager = accountManager
