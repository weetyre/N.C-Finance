from .DyStockStopMode import *
from ...DyStockTradeCommon import *

#止损模式
class DyStockStopLossPnlRatioMode(DyStockStopMode):
    
    def __init__(self, accountManager, pnlRatio):#盈利率（-5%，说白了还是亏了）
        super().__init__(accountManager)

        self._pnlRatio = pnlRatio

    def onTicks(self, ticks):
        for code, pos in self._accountManager.curPos.items():
            tick = ticks.get(code)
            if tick is None:
                continue

            if pos.pnlRatio < self._pnlRatio:# 小于设置的止损率，那就需要关闭持仓
                self._accountManager.closePos(tick.datetime, code, getattr(tick, DyStockTradeCommon.sellPrice), DyStockSellReason.stopLoss, tickOrBar=tick)

    def onBars(self, bars):
        self.onTicks(bars)
