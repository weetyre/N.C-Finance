import traceback

from ...Data.Engine.DyStockDataEngine import *
from EventEngine.DyEvent import *
from ..DyStockSelectCommon import *
from DyCommon.DyCommon import *


class DyStockSelectSelectEngine(object):
    """
        选股引擎(包含指数和股票，但没有基金)
        数据（日线和Tick）是基于最新的复权因子前复权，包含价格和成交量
        基于选股的实盘策略回测和交易时，一定要做除复权的正向逆向转换
        若日线选股和Tick选股同时激活，首先先执行日线选股，然后再根据日线选股的结果载入对应的Tick数据，进行Tick选股。
        可以认为Tick选股是对日线选股的进一步细化。
    """


    def __init__(self, eventEngine, info, registerEvent=True):
        self._eventEngine = eventEngine
        self._info = info

        self._testedStocks = None# 会由事件确认

        self._init()

        self._dataEngine = DyStockDataEngine(self._eventEngine, self._info, False)
        self._progress = DyProgress(self._info)

        self._daysEngine = self._dataEngine.daysEngine

        if registerEvent:
            self._registerEvent()

        # For日线数据补全
        errorInfo = DyErrorInfo(eventEngine)
        self._errorDataEngine = DyStockDataEngine(eventEngine, errorInfo, registerEvent=False)
        self._errorDaysEngine = self._errorDataEngine.daysEngine

        # 独立于daysEnigne，因为ticksEngine载入数据时，需要载入日线数据做参照。
        # 这样可以避免先前@self._daysEngine载入的数据被污染。
        self._ticksEngine = self._errorDataEngine.ticksEngine
    # 停止
    def stop(self):
        self._isStopped = True
    # 初始化
    def _init(self):
        self._isStopped = False# 停止了么？

        self._strategy = None

        self._codes = None # [code]

        # 日线相关数据
        self._isDays = False
        self._startDay = None # 策略的开始交易日
        self._endDay = None # 策略的结束交易日

        # @DyStockSelectStrategyTemplate.autoFillDays引入的相关变量。只有@autoFillDays is True时记录。
        self._onDaysLoadDates = None # [ , ], 策略@onDaysLoad的返回值。主要是为了切片策略指定日期范围的日线数据。
        self._expectedDaysSize = None # 期望载入日线数据的大小，以多少日期算。只有@autoFillDays is True并且是策略相对载入时, 记录该值。
        self._baseDay = None

        # tick相关数据
        self._isTicks = False
        self._startTicksDay = None
        self._endTicksDay = None
        # 返回结果
        self._result = None
        self._resultForTrade = None
    # 载入日数据
    def _onLoadDays(self):
        # 获取策略需要载入数据的日期范围
        startDate, endDate = self._strategy.onDaysLoad()
        if startDate is None:
            return True # 由策略控制载入数据的日期范围，也就是说策略必须要实现onLoadDays和onLoadTicks中的一个。

        # 策略需要补全缺失的日线数据，从策略返回的原始日期范围数据
        if self._strategy.autoFillDays:# 自动载入，输入自动载入区间
            self._onDaysLoadDates = [startDate, endDate]

        self._startDay = startDate
        self._endDay = endDate

        # 相对日期载入数据, 得到[startDate, baseDate, n]序列，对于高换手，end = -1
        if isinstance(endDate, int):

            # 策略需要补全缺失的日线数据并且是相对载入
            if self._onDaysLoadDates is not None:
                self._expectedDaysSize = abs(endDate) + 1# 这个来决定之后是否要自动补全

            if endDate < 0:
                baseDate = startDate
                startDate = endDate
                n = 0
            else:
                baseDate = startDate
                startDate = 0
                n = endDate

        else: # 绝对日期载入数据
            baseDate = endDate
            n = 0

        # 调整载入数据日期
        dates = self._strategy.onPostDaysLoad(startDate, baseDate, n)

        # 从股票数据引擎载入数据. 如果策略指定了codes，则优先codes
        if not self._daysEngine.load(dates, codes=self._testedStocks if self._codes is None else self._codes):# 如果策略关注代码为空，这个codes是刚才调用之前设置好的，none载入全部股票
            return False

        # 设置日线相关数据
        self._isDays = True # 设置日线相关数据
        # 这是日线数据同一日期
        if isinstance(self._endDay, int):
            self._startDay = self._daysEngine.tDaysOffset(self._startDay, 0)
            self._endDay = self._daysEngine.tDaysOffset(self._startDay, self._endDay)
        else:
            self._startDay = self._daysEngine.tDaysOffset(self._startDay, 0)
            self._endDay = self._daysEngine.tDaysOffset(self._endDay, 0)

        if self._endDay < self._startDay:
            self._startDay, self._endDay = self._endDay, self._startDay# 重新确定载入顺序

        self._baseDay = self._daysEngine.tDaysOffset(baseDate, 0)# 最后返回基准日期

        return True
    # 载入tick数据
    def _onLoadTicks(self):
        # 获取策略需要载入数据的日期范围
        startDate, endDate = self._strategy.onTicksLoad()# 返回None, None则说明不做Tick数据载入。
        if startDate is None:
            return True # 由策略控制载入数据的日期范围，也就是说策略必须要实现onLoadDays和onLoadTicks中的一个

        self._startTicksDay = startDate
        self._endTicksDay = endDate

        # 相对日期载入数据, 得到[startDate, baseDate, n]序列
        if isinstance(endDate, int):
            if endDate < 0:
                baseDate = startDate
                startDate = endDate
                n = 0
            else:
                baseDate = startDate
                startDate = 0
                n = endDate

        else: # 绝对日期载入数据
            baseDate = endDate
            n = 0

        if not self._isDays:
            # 调整载入数据日期
            dates = self._strategy.onPostDaysLoad(startDate, baseDate, n)

            # 从股票数据引擎载入日线数据，主要是为了引擎计算其它日线指标用. 如果策略指定了codes，则优先codes
            if not self._daysEngine.load(dates, codes=self._testedStocks if self._codes is None else self._codes):
                return False

        # 设置ticks相关数据
        self._isTicks = True

        # 对@self._endTicksDay不做类似日线数据的统一日期处理，这是因为日线数据的载入是所有股票统一时间周期载入。
        # 而Ticks的数据载入则是每个股票的Ticks分别载入。

        return True
    # 第三步调用load函数
    def _onLoad(self):
        # get loaded codes
        self._codes = self._strategy.onCodes()# 先载入策略需要的代码，返回None 全部载入

        # days
        if not self._onLoadDays():
            return False

        # ticks
        if not self._onLoadTicks():
            return False

        return True
    # 补充个股日线数据
    def _autoFillDays(self, code, orgDf):
        """
            补全个股日线数据
            @orgDf: 原始切片日线数据
        """
        # 数据是完整的
        if orgDf is not None and orgDf.shape[0] == self._expectedDaysSize:# 就是几天
            return orgDf

        # 策略优化自动补全日线数据
        if self._strategy.optimizeAutoFillDays:
            if orgDf is None or self._baseDay not in orgDf.index: # 基准日期不在原始切片数据里，则没有补全的意义
                return None

        if not self._errorDaysEngine.loadCode(code, self._onDaysLoadDates):# 载入的日期，注：不用管最后一个日期统一化，因为都是一样得
            return orgDf

        return self._errorDaysEngine.getDataFrame(code)
    # 运行日线数据
    def _runDaysLoop(self):
        if not self._isDays:
            return

        self._info.print("开始运行日线数据...")

        # init progress
        self._progress.init(len(self._daysEngine.stockAllCodesFunds), 100, 5)# 单步

        # index loop
        for index in self._daysEngine.stockIndexes:# 指数4支
            df = self._daysEngine.getDataFrame(index, self._startDay, self._endDay)# 之后都是更具这个自动载入日计算
            if df is not None:
                self._strategy.onIndexDays(index, df)

            self._progress.update()

        # ETF loop
        for etfCode in self._daysEngine.stockFunds:# 基金3支
            df = self._daysEngine.getDataFrame(etfCode, self._startDay, self._endDay)
            if df is not None:
                self._strategy.onEtfDays(etfCode, df)

            self._progress.update()

        # stock loop
        for code in self._daysEngine.stockCodes:# 更新普通股票
            df = self._daysEngine.getDataFrame(code, self._startDay, self._endDay)

            # 策略需要补全数据
            if self._expectedDaysSize is not None:
                df = self._autoFillDays(code, df)# 会输入df进行验证，进行数据补全，有的时候无法补全数据

            if df is not None or self._strategy.fullyPushDays:
                try:
                    self._strategy.onStockDays(code, df)# 每一个股票，固定周期遍历
                except AssertionError:
                    raise
                except Exception as ex:
                    if DyStockSelectCommon.enableSelectEngineException:# 是否打卡股票选股异常的捕捉，不打开
                        self._info.print('{0}[{1}]: onStockDays异常:{2}'.format(code, self._daysEngine.stockAllCodes[code], repr(ex)), DyLogData.error)

            self._progress.update()

        self._info.print("日线数据运行完成")
    # 紧接着运行tick数据
    def _runTicksLoop(self):
        if not self._isTicks:
            return

        codes = self._strategy.getResultCodes() if self._isDays else self._daysEngine.stockCodes# 根据日线数据获取选股结果代码，否则获取载入代码

        self._info.print("开始运行Ticks数据，总共{0}只股票...".format(len(codes)))

        # init progress
        self._progress.init(len(codes), 100, 5)

        for code in codes:
            if self._ticksEngine.loadCodeN(code, [self._startTicksDay, self._endTicksDay]):

                dfs = self._ticksEngine.getDataFrame(code, adj=True, continuous=self._strategy.continuousTicks)# 基于最新的因子前复权获得
                try:
                    self._strategy.onStockTicks(code, dfs)
                except AssertionError:
                    raise
                except Exception as ex:
                    if DyStockSelectCommon.enableSelectEngineException:
                        self._info.print('{0}[{1}]: onStockTicks异常:{2}'.format(code, self._daysEngine.stockAllCodes[code], repr(ex)), DyLogData.error)

            self._progress.update()

        self._info.print("Ticks数据运行完成")
    # 第四步运行loop选股策略
    def _runLoop(self):
        self._info.print("开始运行选股策略: {0}".format(self._strategy.chName), DyLogData.ind)

        self._runDaysLoop()
        self._runTicksLoop()
    # 第二步调用run函数
    def _run(self):
        # load
        if not self._onLoad():
            return False

        # init strategy
        try:
            self._strategy.onInit(self._dataEngine, self._errorDataEngine)
        except Exception as ex:
            traceback.print_exc()
            self._info.print('策略onInit异常: {}'.format(ex), DyLogData.error)
            return False

        # run loop
        self._runLoop()

        # done for strategy
        self._strategy.onDone()

        # done for Engine
        self._result = self._strategy.onDoneForEngine(self._dataEngine, self._errorDataEngine)# 这里是最终的结果

        # to trade
        self._resultForTrade = self._strategy.toTrade()# 为了实盘选股的结果，一般为false

        return True
    #
    @property
    def result(self):
        """ 选股结果 """
        return self._result
    #
    @property
    def resultForTrade(self):
        """ 为实盘的选股结果 """
        return self._resultForTrade
    # 会在CTA里面调设置调试股票
    def setTestedStocks(self, codes=None):
        self._testedStocks = codes
    # 先运行这个
    def runStrategy(self, strategyCls, paramters):
        self._info.print("开始准备运行选股策略: {0}".format(strategyCls.chName), DyLogData.ind)
        self._info.initProgress()# 初始化进度条

        # init
        self._init()# 先执行一遍初始化

        # create strategy instance
        self._strategy = strategyCls(paramters, self._info)

        # run
        if self._run():
            # ack，之后返回结果
            event = DyEvent(DyEventType.stockSelectStrategySelectAck)# 运行完之后就确认
            event.data['class'] = strategyCls
            event.data['result'] = self._result
            event.data['baseDate'] = self._strategy.baseDate

            self._eventEngine.put(event)

            # finish
            self._eventEngine.put(DyEvent(DyEventType.finish))# 发送一个所有任务都完成的操作

            ret = True
        else:
            # fail
            self._eventEngine.put(DyEvent(DyEventType.fail))

            ret = False

        return ret
    # 获取策略类以及参数运行策略，其他地方put一个请求事件就开始运行，一按下按钮就开始在这里运行
    def _stockSelectStrategySelectReqHandler(self, event):
        # unpack
        strategyCls = event.data['class']
        paramters = event.data['param']

        self.runStrategy(strategyCls, paramters)
    # 设置选股的测试股票
    def _stockSelectTestedCodesHandler(self, event):
        self._testedStocks = event.data

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockSelectStrategySelectReq, self._stockSelectStrategySelectReqHandler, DyStockSelectEventHandType.engine)# 0号运行
        self._eventEngine.register(DyEventType.stockSelectTestedCodes, self._stockSelectTestedCodesHandler, DyStockSelectEventHandType.engine)# 0号运行
