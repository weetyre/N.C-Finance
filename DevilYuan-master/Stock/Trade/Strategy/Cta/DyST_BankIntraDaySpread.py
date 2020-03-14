from ..DyStockCtaTemplate import *


class DyST_BankIntraDaySpread(DyStockCtaTemplate):
    # 子类覆盖父类的属性以及方法
    name = 'DyST_BankIntraDaySpread'
    chName = '银行日内价差'

    backTestingMode = 'bar1m'

    broker = 'yh'

    # 策略实盘参数
    codes = ['601988.SH', '601288.SH', '601398.SH', '601939.SH']
    spread = 0.5


    def __init__(self, ctaEngine, info, state, strategyParam=None): # 那么这个策略状态也是回测
        super().__init__(ctaEngine, info, state, strategyParam)# 如果是回测，那么这个CT引擎就是回测CTA引擎

        self._curInit()
    #
    def _onOpenConfig(self):
        self._monitoredStocks.extend(self.codes)# 扩充list
    # 模板已经初始化过了，所以自己就不用特殊的初始化了。
    def _curInit(self, date=None):
        pass

    @DyStockCtaTemplate.onOpenWrapper# 调用完父类调用子类
    def onOpen(self, date, codes=None):
        # 当日初始化
        self._curInit(date)

        self._onOpenConfig()# 加入策略监控数据

        return True
    #
    def onTicks(self, ticks):
        """
            收到行情TICKs推送
            @ticks: {code: DyStockCtaTickData}
        """
        
        if self._curPos:
            code = list(self._curPos)[0]
            tick = ticks.get(code)
            if tick is None:
                return

            increase = (tick.price - tick.preClose)/tick.preClose*100

            spreads = {}
            for code_ in self.codes:
                if code == code_:
                    continue
                
                tick_ = ticks.get(code_)
                if tick_ is None:
                    continue

                spread = increase - (tick_.price - tick_.preClose)/tick_.preClose*100
                if spread >= self.spread:
                    spreads[code_] = spread

            codes = sorted(spreads, key=lambda k: spreads[k], reverse=True)
            if codes:
                self.closePos(ticks.get(code))

                self.buyByRatio(ticks.get(codes[0]), 50, self.cAccountLeftCashRatio)
        # 刚回测时没有当前持仓
        else:
            increases = {}
            for code in self.codes:# 循环遍历每一个过滤后的股票
                tick = ticks.get(code) # 
                if tick is None:
                    continue
                # 这里就贯彻着银行日内差的策略
                increases[code] = (tick.price - tick.preClose)/tick.preClose*100

            codes = sorted(increases, key=lambda k: increases[k]) # 更具日内差，升序排列，最大的放后面
            if codes:
                self.buyByRatio(ticks.get(codes[0]), 50, self.cAccountLeftCashRatio)# 买入差别最小的
    # 
    def onBars(self, bars):
        self.onTicks(bars)
