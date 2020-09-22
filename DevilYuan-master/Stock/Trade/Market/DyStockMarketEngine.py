from datetime import *

from EventEngine.DyEvent import *
from ..DyStockTradeCommon import *
from ..Strategy.DyStockCtaBase import *
from ...Common.DyStockCommon import *
from .DyStockSinaQuotation import *

# 实时行情监控（新浪，监控股票以及 tick timer， 推送开盘稳定tick ）
class DyStockMarketEngine(object):
    """
        Real time monitor stock market
        成交额数据问题：
            - 创小板指数成交金额错误
            - 深证成指个股累加成交金额错误
    """

    # 深市是3秒一次更新，沪市是5秒一次更新
    # 由于可能会交错更新，所以只要哪个有更新，则推入所有Ticks
    shIndexSinaCode = 'sh000001'
    szIndexSinaCode = 'sz399001'

    openStableCount = 90 # 集合竞价后的1分半时的Ticks作为稳定的开盘Ticks


    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._sinaQuotation = DyStockSinaQuotation(self._eventEngine, self._info)# 实例化新浪tick数据获取
        self._curDay = None

        self._registerEvent()

        self._curInit()
    # 当日初始化，新浪，默认监控指数，以及监控和开盘计数器
    def _curInit(self):
        # 防止一键挂机后，重复初始化
        curDay = datetime.now().strftime("%Y-%m-%d")
        if curDay == self._curDay:
            return False

        self._curDay = curDay

        # init sina
        self._sinaQuotation.init()
        self._sinaQuotation.addIndexes(list(DyStockCommon.indexes) + [DyStockCommon.cybzIndex, DyStockCommon.zxbzIndex])# 四大板块加创业板和中小板

        self._monitoredStocks = [] # exclude indexes
        self._latestShIndexSinaTick = None # 最新上证指数Sina Tick
        self._latestSzIndexSinaTick = None # 最新深证成指Sina Tick

        # 交易日9:25:00 ~ 9:30:00之间是比较特别的时间
		# 市场引擎只推送集合竞价后的一个稳定的Ticks
		# 原则上这部分应该由CTA引擎负责，但市场引擎Ticks推送优化后，CTA引擎没法知道集合竞价后的哪一个Ticks是稳定的。
		# 所以引入开盘计数器，以推送一个稳定的Ticks。
        self._openCount = 0 # 为了推送一个稳定的Ticks。

        return True
    # 就会发到这里来，由simuTrader发送而来，还有就是策略启动之后（按下按钮后，也会发送）
    def _stockMarketMonitorHandler(self, event):
        """ 添加要监控的股票, 不含指数
            @event.data: [code]
        """
        newCodes = []
        for code in event.data:
            if code not in self._monitoredStocks and code not in DyStockCommon.indexes:
                self._monitoredStocks.append(code)# 重点加到这个变量里
                newCodes.append(code)

        if newCodes:# 这里除了默认的六个，会添加额外的监控股票
            self._sinaQuotation.add(newCodes)# 就是添加到sinaQuatation 那个类，去新浪获取事实状况
    # 是否需要put至事件引擎
    def _isNeedPut(self, stockSinaTickData):
        """
            check if need to put ticks into event egnine
        """
        if not DyStockTradeCommon.enableSinaTickOptimization:#  打开新浪Tick数据的优化，主要是调试新浪的Tick数据
            return True

        # 深证成指
        # 由于深市更新频率高，所以先判断深市
        szIndexSinaTick = stockSinaTickData.get(self.szIndexSinaCode)

        # check if time of SZ index tick changed
        if szIndexSinaTick is not None:
            if self._latestSzIndexSinaTick is None:# 如果最新的没有，那么赋值最新的
                self._latestSzIndexSinaTick = szIndexSinaTick
                return True

            else:
                # 处理集合竞价后和开盘之间的Ticks，只推送这段时间的一个稳定的Ticks
                if '09:25:00' <= szIndexSinaTick['time'] < '09:30:00':
                    self._openCount += 1
                    if self._openCount != self.openStableCount:# 90秒
                        return False# 要不一直返回False

                if self._latestSzIndexSinaTick['time'] != szIndexSinaTick['time']:
                    self._latestSzIndexSinaTick = szIndexSinaTick#
                    return True

        # 上证指数 5秒一更新，所以这个后获取，只在深圳指数没有的时候才会推送
        shIndexSinaTick = stockSinaTickData.get(self.shIndexSinaCode)

        # check if time of SH index tick changed
        if shIndexSinaTick is not None:
            if self._latestShIndexSinaTick is None:
                self._latestShIndexSinaTick = shIndexSinaTick
                return True

            else:
                if self._latestShIndexSinaTick['time'] != shIndexSinaTick['time']:
                    self._latestShIndexSinaTick = shIndexSinaTick
                    return True

        return False

    #@DyTime.instanceTimeitWrapper 每个1秒获取板块以及指数的数据（6个），以及监控数据
    def _timerHandler(self, event):
        try:
            if DyStockTradeCommon.enableTimerLog:# 默认不打开，因为调试好了新浪tick引擎
                print('@DyStockMarketEngine._timerHandler')

            # get ticks from Sina
            try:
                stockSinaTickData = self._sinaQuotation.get()# 从这里获取
            except Exception as ex:
                self._info.print("self._sinaQuotation.get()异常: {}".format(repr(ex)), DyLogData.warning)
                return

            if DyStockTradeCommon.enableTimerLog:
                print('Get {} codes from Sina'.format(len(stockSinaTickData)))
                if self.szIndexSinaCode in stockSinaTickData:
                    print(stockSinaTickData[self.szIndexSinaCode])

            # If need to put changed ticks into Engine
            if self._isNeedPut(stockSinaTickData):
                # convert
                ctaTickDatas = self._convert(stockSinaTickData)# 转换数据格式

                self._putTickEvent(ctaTickDatas) # 推送tick事件，为了实时更新,包括日后的追踪热点实时更新

        except Exception as ex:
            self._info.print("{}._timerHandler异常: {}".format(self.__class__.__name__, repr(ex)), DyLogData.warning)

    #@DyTime.instanceTimeitWrapper 转换从新浪获取的股票的数据格式
    def _convert(self, stockSinaTickData):
        """
            convert Sina stock tick data to DyStockCtaTickData
        """
        ctaTickDatas = {} # {code: DyStockCtaTickData}
        for code, data in stockSinaTickData.items():
            if data['now'] > 0: # 去除停牌股票。对于开盘，有些股票可能没有任何成交，但有当前价格。
                ctaTickData = DyStockCtaTickData(code, data)# 生成tick实例
                ctaTickDatas[ctaTickData.code] = ctaTickData

        return ctaTickDatas
    # 注册事件
    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockMarketMonitor, self._stockMarketMonitorHandler, DyStockTradeEventHandType.stockSinaQuotation)
        self._eventEngine.registerTimer(self._timerHandler, DyStockTradeEventHandType.stockSinaQuotation, 1)
        # 一键挂机，交易日开始，交易日结束，虽然事件名不一样，但是进去就是注册Timer
        self._eventEngine.register(DyEventType.beginStockTradeDay, self._beginStockTradeDayHandler, DyStockTradeEventHandType.stockSinaQuotation)
        self._eventEngine.register(DyEventType.endStockTradeDay, self._endStockTradeDayHandler, DyStockTradeEventHandType.stockSinaQuotation)
    # 推送tick事件，为了实时更新,包括日后的追踪热点实时更新
    def _putTickEvent(self, ctaTickDatas):
        if not ctaTickDatas:
            return

        event = DyEvent(DyEventType.stockMarketTicks)# 这个一put 会更新多处的数据，对应的6个功能函数处理
        event.data = ctaTickDatas

        self._eventEngine.put(event)
    #这里开始timer Tick monitor 相关函数更新，定时更新
    def _beginStockTradeDayHandler(self, event):
        if self._curInit():# 防止一件挂机重复初始化，以及重复注册Timer
            self._info.print('股票行情引擎: 开始交易日[{}]'.format(self._curDay), DyLogData.ind2)

            self._eventEngine.registerTimer(self._timerHandler, DyStockTradeEventHandType.stockSinaQuotation, 1)
    # 结束交易日（一键挂机如果不是交易日，或者超时，会调用这个）
    def _endStockTradeDayHandler(self, event):
        self._info.print('股票行情引擎: 结束交易日[{}]'.format(self._curDay), DyLogData.ind2)

        self._curDay = None
        # 解注册获取TICK timer
        self._eventEngine.unregisterTimer(self._timerHandler, DyStockTradeEventHandType.stockSinaQuotation, 1)
