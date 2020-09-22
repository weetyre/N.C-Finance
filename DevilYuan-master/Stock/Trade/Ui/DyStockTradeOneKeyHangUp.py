from datetime import datetime
from time import sleep
import threading

import tushare as ts

from EventEngine.DyEvent import *
from DyCommon.DyCommon import *
from DyCommon.DyScheduler import DyScheduler
from Stock.Common.DyStockCommon import DyStockCommon


class DyStockTradeOneKeyHangUp(object):
    """
        股票交易一键挂机
        用户必须先启动好策略，然后才能一键挂机。
    """
    testMode = False
    testModeInterval = 60 # 单位秒


    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._scheduler = None
        self._tradeDays = {}
    # 检查今天是否是交易日
    def _checkDay(self):
        """
            check current day is trade day or not
            @return: bool,
                     None - error
        """
        curDay = datetime.now().strftime("%Y-%m-%d")

        # set trade days by data gotten from TuShare
        if curDay not in self._tradeDays:# 刚开始是空
            for _ in range(3):# 尝试三遍
                if self._setTradeDays(curDay):# 更新 self._tradeDays
                    break

                sleep(1)

        isTradeDay = self._tradeDays.get(curDay)
        if isTradeDay is None:
            self._info.print("一键挂机: TuShare缺失{}交易日数据".format(curDay), DyLogData.error)
           
        return isTradeDay # 返回TF
    # 一天的开始
    def _beginDay(self):
        if self._checkDay() or self.testMode:
            self._eventEngine.put(DyEvent(DyEventType.beginStockTradeDay))# 交易日开始，注册Tick timer
    # 一天的结束
    def _endDay(self):
        if self._checkDay() or self.testMode:
            self._eventEngine.put(DyEvent(DyEventType.endStockTradeDay))# 交易日结束,解除注册
    # 今日是否为交易日
    def _setTradeDays(self, startDate):
        ret = False
        if DyStockCommon.tuShareProToken: # prefer TuSharePro firstly
            ret = self._setTradeDaysViaTuSharePro(startDate) # 从PRo获取

        if not ret: #如果 获取失败再从一般的接口获取
            ret = self._setTradeDaysViaTuShare(startDate)

        return ret
    # 一般的Tushare获取
    def _setTradeDaysViaTuShare(self, startDate):
        print("TuShare: 获取交易日数据[{}]".format(startDate))

        try:
            df = ts.trade_cal()

            df = df.set_index('calendarDate')
            df = df[startDate:]

            # get trade days
            dates = DyTime.getDates(startDate, df.index[-1], strFormat=True)
            self._tradeDays = {}
            for date in dates:
                if df.ix[date, 'isOpen'] == 1:
                    self._tradeDays[date] = True
                else:
                    self._tradeDays[date] = False

        except Exception as ex:
            self._info.print("一键挂机: 从TuShare获取交易日[{}]数据异常: {}".format(startDate, str(ex)), DyLogData.warning)
            return False

        return True
    # 从Pro版本获取是否是交易日，顺便更新 self._tradeDays
    def _setTradeDaysViaTuSharePro(self, startDate):
        print("TuSharePro: 获取交易日数据[{}]".format(startDate))

        ts.set_token(DyStockCommon.tuShareProToken)
        pro = ts.pro_api()

        proStartDate = startDate.replace('-', '')# 返回如20200321
        try:
            df = pro.trade_cal(exchange='', start_date=proStartDate)# 由给定日期获取交易日

            df = df.set_index('cal_date')# 已这一列作为索引
            df = df[proStartDate:]# 从给定日期开始往后的数据

            # get trade days ['2020-03-21','2020-03-22',.........] end = 今天的最后一天，或者给的数据最后一天的 年-月-日
            dates = DyTime.getDates(startDate, df.index[-1][:4] + '-' + df.index[-1][4:6] + '-' + df.index[-1][6:], strFormat=True)
            self._tradeDays = {}# 每一天返回TF
            for date in dates:# ['2020-03-21','2020-03-22',.........]
                if df.loc[date.replace('-', ''), 'is_open'] == 1:
                    self._tradeDays[date] = True
                else:
                    self._tradeDays[date] = False

        except Exception as ex:
            self._info.print("一键挂机: 从TuSharePro获取交易日[{}]数据异常: {}".format(startDate, ex), DyLogData.warning)
            return False

        return True

    def _testModeRun(self):
        while True:
            sleep(self.testModeInterval)
            self._beginDay()

            sleep(self.testModeInterval)
            self._endDay()
    # 先从这里启动一键挂机的功能
    def start(self):
        assert self._scheduler is None# 首先是空的实例

        isTradeDay = self._checkDay()
        if isTradeDay is None:
            return False

        # 推送endTradeDay事件
        if not isTradeDay or datetime.now().strftime('%H:%M:%S') > '15:45:00':
            self._eventEngine.put(DyEvent(DyEventType.endStockTradeDay))# 不是交易日，或者超时，交易日结束

        if self.testMode: # 测试模式 一般是False
            threading.Thread(target=self._testModeRun).start()
        else:
            self._scheduler = DyScheduler()# 实例化任务调度器

            self._scheduler.addJob(self._beginDay, {1, 2, 3, 4, 5}, '08:30:00')# 调的是函数指针
            self._scheduler.addJob(self._endDay, {1, 2, 3, 4, 5}, '15:45:00')

            self._scheduler.start()

        return True

    def stop(self):
        if self._scheduler is None:
            return

        self._scheduler.shutdown()
        self._scheduler = None

