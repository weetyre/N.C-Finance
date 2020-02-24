import os
import json

from DyCommon.DyCommon import *
from EventEngine.DyEvent import *
from ..DyStockDataCommon import *
from ...Trade.Broker.DyStockTradeBrokerEngine import *


class DyStockDataStrategyDataPrepareEngine(object):
    """ 生成股票实盘准备数据的引擎
        策略需要实现prepare接口
    """

    def __init__(self, eventEngine, dataEngine, info, registerEvent=True):
        self._eventEngine = eventEngine
        self._dataEngine = dataEngine
        self._info = info

        self._testedStocks = None

        self._strategyClsCount = 0 #策略类的数目
        self._isStopped = False #默认并没有停止

        if registerEvent:
            self._registerEvent()
    #准备数据写入本地文件
    def _writePreparedData(self, strategyCls, date, data):
        """
            file name is like 'Program\Strategy\strategyCls.chName\date\preparedData.json'
        """
        path = DyCommon.createPath('Stock/Program/Strategy/{}/{}'.format(strategyCls.chName, date))
        fileName = os.path.join(path, 'preparedData.json')
        with open(fileName, 'w') as f:
            f.write(json.dumps(data, indent=4, cls=DyJsonEncoder))
    #实盘准备数据
    def _stockStrategyDataPrepare(self, date, strategyCls):
        self._info.print('开始生成策略[{0}]实盘准备数据[{1}]...'.format(strategyCls.chName, date), DyLogData.ind1)

        # init
        data = None
        savedDate = date

        # get latest trade day targeted with @date
        date = self._dataEngine.daysEngine.tDaysOffsetInDb(date)
        if date is not None:
            if date != savedDate:
                self._info.print('{0}转成最近交易日{1}'.format(savedDate, date))

            # call策略prepare接口
            errorInfo = DyErrorInfo(self._eventEngine)
            errorDataEngine = self._dataEngine.__class__(self._eventEngine, errorInfo, registerEvent=False)
            data = strategyCls.prepare(date, self._dataEngine, self._info, self._testedStocks, errorDataEngine)

        if data is None:
            self._info.print('生成策略[{0}]实盘准备数据[{1}]失败'.format(strategyCls.chName, date), DyLogData.error)
            return

        # write to json file
        self._writePreparedData(strategyCls, date, data)

        self._info.print('策略[{0}]实盘准备数据[{1}]生成完成'.format(strategyCls.chName, date), DyLogData.ind1)
    #读取保存的数据
    def _readSavedData(self, strategyCls, date):
        """
            读取策略@date收盘保存的数据。主要是为了获取持仓代码表。
        """
        path = DyCommon.createPath('Stock/Program/Strategy/{}/{}'.format(strategyCls.chName, date))
        fileName = os.path.join(path, 'savedData.json')

        try:
            with open(fileName) as f:
                savedData = json.load(f)

                return savedData

        except Exception as ex:
            pass

        return None
    #保存实盘持仓数据
    def _writePreparedPosData(self, strategyCls, date, data):
        """
            file name is like 'Program\Strategy\strategyCls.chName\date\preparedPosData.json'
        """
        path = DyCommon.createPath('Stock/Program/Strategy/{}/{}'.format(strategyCls.chName, date))
        fileName = os.path.join(path, 'preparedPosData.json')
        with open(fileName, 'w') as f:
            f.write(json.dumps(data, indent=4, cls=DyJsonEncoder))
    #实盘持仓准备数据
    def _stockStrategyPosDataPrepare(self, date, strategyCls):
        self._info.print('开始生成策略[{0}]实盘持仓准备数据[{1}]...'.format(strategyCls.chName, date), DyLogData.ind1)

        # init
        data = None
        savedDate = date

        # get latest trade day targeted with @date
        date = self._dataEngine.daysEngine.tDaysOffsetInDb(date)
        if date is not None:
            if date != savedDate:
                self._info.print('{0}转成最近交易日{1}'.format(savedDate, date))#向前，也就是时间早

            # read saved data
            savedData = self._readSavedData(strategyCls, date)
            
            # get pos codes
            posCodes = None
            if savedData:
                posCodes = savedData.get('pos')

            if posCodes:
                posCodes = list(posCodes)

            # call策略preparePos接口
            errorInfo = DyErrorInfo(self._eventEngine)
            errorDataEngine = self._dataEngine.__class__(self._eventEngine, errorInfo, registerEvent=False)
            data = strategyCls.preparePos(date, self._dataEngine, self._info, posCodes, errorDataEngine)

        if data is None:
            self._info.print('生成策略[{0}]实盘持仓准备数据[{1}]失败'.format(strategyCls.chName, date), DyLogData.error)
            return

        # write to json file
        self._writePreparedPosData(strategyCls, date, data)

        self._info.print('策略[{0}]实盘持仓准备数据[{1}]生成完成'.format(strategyCls.chName, date), DyLogData.ind1)
    #
    def _stockStrategySimuTraderPosCloseUpdate(self, date, strategyCls):
        """
            更新策略绑定的模拟交易接口的持仓收盘数据
        """
        if strategyCls.broker is None or strategyCls.broker[:4] != 'simu':
            return

        traderCls = DyStockTradeBrokerEngine.traderMap[strategyCls.broker]

        self._info.print('开始更新策略[{0}]绑定的交易接口[{1}]的持仓收盘数据[{2}]...'.format(strategyCls.chName, traderCls.brokerName, date), DyLogData.ind1)

        # init
        savedDate = date

        # get latest trade day targeted with @date
        date = self._dataEngine.daysEngine.tDaysOffsetInDb(date)
        if date is None:
            self._info.print('更新策略[{0}]绑定的交易接口[{1}]的持仓收盘数据[{2}]失败'.format(strategyCls.chName, traderCls.brokerName, savedDate), DyLogData.error)
            return
        
        if date != savedDate:
            self._info.print('{0}转成最近交易日{1}'.format(savedDate, date))

        # 更新持仓收盘价
        traderCls.updatePosClose(self._eventEngine, self._info)

        self._info.print('更新策略[{0}]绑定的交易接口[{1}]的持仓收盘数据[{2}]完成'.format(strategyCls.chName, traderCls.brokerName, date), DyLogData.ind1)
    #
    def _stockStrategyDataPrepareHandler(self, event):
        date = event.data['date']
        classes = event.data['classes']

        if self._strategyClsCount == 0: # new start
            self._strategyClsCount = len(classes)
        else:
            if self._isStopped:#如果停止了，重置
                # reset
                self._strategyClsCount = 0
                self._isStopped = False

                # send stopAck
                self._eventEngine.put(DyEvent(DyEventType.stopAck))#然后发送停止确认给UI

                return

        # only process the first one
        self._stockStrategyDataPrepare(date, classes[0])#实盘准备数据
        self._stockStrategyPosDataPrepare(date, classes[0])#实盘持仓准备数据
        self._stockStrategySimuTraderPosCloseUpdate(date, classes[0])#更新策略绑定的模拟交易接口的持仓收盘数据

        self._strategyClsCount -= 1

        # check if finish or not
        if self._strategyClsCount == 0: # finish
            self._eventEngine.put(DyEvent(DyEventType.finish))#发送结束确认

        else:
            # send left
            event = DyEvent(DyEventType.stockStrategyDataPrepare)
            event.data['date'] = date
            event.data['classes'] = classes[1:]

            self._eventEngine.put(event)#再次发送剩余的策略类，然后再注册相同事件
    #停止函数
    def _stopReqHandler(self, event):

        if self._strategyClsCount == 0:
            # send stopAck directly
            self._eventEngine.put(DyEvent(DyEventType.stopAck))
        else:
            self._isStopped = True #如果有，在上一个函数重置

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockStrategyDataPrepare, self._stockStrategyDataPrepareHandler, DyStockDataEventHandType.strategyDataPrepare) # 策略数据准备
        self._eventEngine.register(DyEventType.stopStockStrategyDataPrepareReq, self._stopReqHandler, DyStockDataEventHandType.strategyDataPrepare) #停止策略数据准备得请求
        self._eventEngine.register(DyEventType.stockSelectTestedCodes, self._stockSelectTestedCodesHandler, DyStockDataEventHandType.strategyDataPrepare)# 调试股票事件

    def _stockSelectTestedCodesHandler(self, event):
        self._testedStocks = event.data
