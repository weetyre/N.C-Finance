from EventEngine.DyEvent import *
from ..DyStockDataCommon import *
from .DyStockMongoDbEngine import *
from ..Gateway.DyStockDataGateway import *
from .DyStockDataTicksEngine import *
from .DyStockDataDaysEngine import *
from .DyStockDataStrategyDataPrepareEngine import *

#股票数据引擎，包括引用日数据以及Tick级别数据引擎
class DyStockDataEngine(object):

    class State:
        sWaitingDays = 'sWaitingDays'
        sWaitingTicks = 'sWaitingTicks'

    def __init__(self, eventEngine, info, registerEvent=True, dbCache=False):
        self._eventEngine = eventEngine
        self._info = info

        self._mongoDbEngine = DyStockMongoDbEngine(self._info, dbCache)
        self._gateway = DyStockDataGateway(self._eventEngine, self._info, registerEvent)

        self._daysEngine = DyStockDataDaysEngine(self._eventEngine, self._mongoDbEngine, self._gateway, self._info, registerEvent)
        self._ticksEngine = DyStockDataTicksEngine(self._eventEngine, self._daysEngine, self._mongoDbEngine, self._gateway, self._info, registerEvent)

        self._strategyDataPrepareEngine = DyStockDataStrategyDataPrepareEngine(self._eventEngine, self, self._info, registerEvent)

        self._isStopped = False
        self._updateDates = None
        self._oneKeyUpdateState = None

        if registerEvent:
            self._registerEvent()

    @property
    def daysEngine(self):
        return self._daysEngine

    @property
    def ticksEngine(self):
        return self._ticksEngine

    @property
    def eventEngine(self):
        return self._eventEngine

    @property
    def info(self):
        return self._info

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockOneKeyUpdate, self._stockOneKeyUpdateHandler)# 一键更新
        self._eventEngine.register(DyEventType.stopStockOneKeyUpdateReq, self._stopStockOneKeyUpdateReqHandler)# 停止一键更新
        self._eventEngine.register(DyEventType.stockDaysCommonUpdateFinish, self._stockDaysCommonUpdateFinishHandler)# 股票日线通用数据更新结束, 也就是股票代码表和交易日数据

        self._eventEngine.register(DyEventType.stopAck, self._stopAckHandler)
        self._eventEngine.register(DyEventType.finish, self._finishHandler)# 所有部分都完成
        self._eventEngine.register(DyEventType.fail, self._failHandler)
    #自动更新日线数据
    def _stockOneKeyUpdateHandler(self, event):
        if self._oneKeyUpdateState is None:

            # 自动更新日线数据
            event = DyEvent(DyEventType.updateStockHistDays)
            event.data = None

            self._eventEngine.put(event)

            self._isStopped = False
            self._updateDates = None
            self._oneKeyUpdateState = DyStockDataEngine.State.sWaitingDays# 更新一键更新状态，在等待
    #停止一键更新请求，首先Stop为True
    def _stopStockOneKeyUpdateReqHandler(self, event):
        self._isStopped = True
        #根据不同状态注册事件
        if self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingDays:
            self._eventEngine.put(DyEvent(DyEventType.stopUpdateStockHistDaysReq))

        elif self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingTicks:
            self._eventEngine.put(DyEvent(DyEventType.stopUpdateStockHistTicksReq))
    #股票数据更新完毕后把数据给这个属性 
    def _stockDaysCommonUpdateFinishHandler(self, event):
        if self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingDays:
            self._updateDates = event.data
    # 所有部分都完成
    def _finishHandler(self, event):
        if self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingDays:
            if self._isStopped:
                self._eventEngine.put(DyEvent(DyEventType.stopAck)) # for UI
                self._oneKeyUpdateState = None

            else:
                if self._updateDates is not None:
                    event = DyEvent(DyEventType.updateStockHistTicks)#那么继续更新Tick数据
                    event.data = self._updateDates

                    self._eventEngine.put(event)

                    self._oneKeyUpdateState = DyStockDataEngine.State.sWaitingTicks#状态改为等待tick数据更新
                else:
                    # UI is waiting for 2 actions, when no need to update ticks, it means ticks updating is finished also.
                    self._eventEngine.put(DyEvent(DyEventType.finish))

                    self._oneKeyUpdateState = None
        #上个状态是Tick，证明更新完了
        elif self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingTicks:
            self._oneKeyUpdateState = None
    #失败处理函数，给UI通知
    def _failHandler(self, event):
        if self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingDays:
            self._eventEngine.put(DyEvent(DyEventType.fail)) # for UI

            self._oneKeyUpdateState = None

        elif self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingTicks:
            self._oneKeyUpdateState = None
    #停止确认函数，响应UI
    def _stopAckHandler(self, event):
        if self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingDays:
            self._eventEngine.put(DyEvent(DyEventType.stopAck)) # for UI
            #把状态设置为None,初始化
            self._oneKeyUpdateState = None

        elif self._oneKeyUpdateState == DyStockDataEngine.State.sWaitingTicks:
            self._oneKeyUpdateState = None
