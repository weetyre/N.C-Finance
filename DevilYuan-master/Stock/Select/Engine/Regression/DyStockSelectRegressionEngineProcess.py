import queue

from DyCommon.DyCommon import *
from EventEngine.DyEvent import *
from EventEngine.DyEventEngine import *
from ..DyStockSelectSelectEngine import *
from ....Common.DyStockCommon import DyStockCommon


def dyStockSelectRegressionEngineProcess(outQueue, inQueue, tradeDays, strategy, codes, histDaysDataSource):
    strategyCls = strategy['class']
    parameters = strategy['param']

    DyStockCommon.defaultHistDaysDataSource = histDaysDataSource# 日线数据源

    dummyEventEngine = DyDummyEventEngine()# 进程处理用一个假的代替引擎即可，因为不需要put事件，或者注册事件，为了处理方便
    queueInfo = DyQueueInfo(outQueue)# 也是用来打印消息的

    selectEngine = DyStockSelectSelectEngine(dummyEventEngine, queueInfo, False)
    selectEngine.setTestedStocks(codes)# 设置调试股票

    for day in tradeDays:
        try:
            event = inQueue.get_nowait()# 为了特殊功能，但是我现在就pass了
        except queue.Empty:
            pass# 直接pass

        parameters['基准日期'] = day# 每一天当作一个基准日期，且基准日期基本属于重设状态

        if selectEngine.runStrategy(strategyCls, parameters):# 先运行选股引擎
            event = DyEvent(DyEventType.stockSelectStrategyRegressionAck)# 紧接着返回结果
            event.data['class'] = strategyCls
            event.data['period'] = [tradeDays[0], tradeDays[-1]]
            event.data['day'] = day
            event.data['result'] = selectEngine.result# 直接返回选股结果

            outQueue.put(event)# 返回结果
        else:# 否则打印信息
            queueInfo.print('回归选股策略失败:{0}, 周期[{1}, {2}], 基准日期{3}'.format(strategyCls.chName, tradeDays[0], tradeDays[-1], day), DyLogData.error)

