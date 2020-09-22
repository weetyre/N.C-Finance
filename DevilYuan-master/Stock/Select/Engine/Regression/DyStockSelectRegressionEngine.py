from .DyStockSelectRegressionEngineProxy import *
from ....Data.Engine.Common.DyStockDataCommonEngine import *
from ....Data.Engine.DyStockMongoDbEngine import *
from DyCommon.DyCommon import *


class DyStockSelectRegressionEngine(object):

    periodNbr = 4 # 一个周期一个进程, 默认是4个
    
    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._progress = DyProgress(self._info)

        self._proxy = DyStockSelectRegressionEngineProxy(self._eventEngine)
        self._testedStocks = None

        self._registerEvent()

    def _stockSelectTestedCodesHandler(self, event):
        self._testedStocks = event.data
    # 回归，这是第一步，返回false只会在必要数据为获取才会返回false，结果已经有分进程返回
    def _regression(self, startDate, endDate, strategyCls, parameters):

        self._progress.reset()# 重设进度条

        # load code table and trade days table
        commonEngine = DyStockDataCommonEngine(DyStockMongoDbEngine(self._info), None, self._info)
        if not commonEngine.load([startDate, endDate]):# 获取对应的数据
            return False

        self._info.print("开始回归策略: {0}[{1}, {2}]...".format(strategyCls.chName, startDate, endDate), DyLogData.ind)

        strategy = {'class':strategyCls, 'param':parameters}
        tradeDays = commonEngine.getTradeDays(startDate, endDate)# 返回list列表

        # init progress
        self._progress.init(len(tradeDays))

        stepSize = (len(tradeDays) + self.periodNbr - 1)//self.periodNbr# 步进，就是周期数目
        if stepSize == 0: return False

        # start processes
        for i in range(0, len(tradeDays), stepSize):# 这里分发不同的进程 i 从0 开始
            self._proxy.startRegression(tradeDays[i:i + stepSize], strategy, self._testedStocks)# 分步进周期进行，且回归结果直接由分进程返回

        return True
    # 选股回归请求，在这里开始第一步处理（按完按钮后）
    def _stockSelectStrategyRegressionReqHandler(self, event):
        # unpack
        strategyCls = event.data['class']
        parameters = event.data['param']
        startDate = event.data['startDate']
        endDate = event.data['endDate']

        # regression
        if not self._regression(startDate, endDate, strategyCls, parameters):
            self._eventEngine.put(DyEvent(DyEventType.fail))
    # 第二步选股回归确认，因为是回归确认结果，所以必须等到所有都结束，才能finish
    def _stockSelectStrategyRegressionAckHandler(self, event):
        self._progress.update()# 更新一下，因为是多进程的，所以，每次outqueue get 之后，都会运行这个

        if self._progress.totalReqCount == 0:# 等总请求数目归零即完成
            self._eventEngine.put(DyEvent(DyEventType.finish))
    # 注册事件
    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockSelectStrategyRegressionReq, self._stockSelectStrategyRegressionReqHandler, DyStockSelectEventHandType.engine)# 都是给号1引擎执行
        self._eventEngine.register(DyEventType.stockSelectStrategyRegressionAck, self._stockSelectStrategyRegressionAckHandler, DyStockSelectEventHandType.engine)
        self._eventEngine.register(DyEventType.stockSelectTestedCodes, self._stockSelectTestedCodesHandler, DyStockSelectEventHandType.engine)


