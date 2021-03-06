from PyQt5 import QtCore

from DyCommon.Ui.DyTableWidget import *
from EventEngine.DyEvent import *
from ...Market.DyStockMarketFilter import *
from ....Common.DyStockCommon import *

#指数行情窗口
class DyStockMarketIndexMonitorWidget(DyTableWidget):

    signal = QtCore.pyqtSignal(type(DyEvent()))

    header = ['名称','最新','涨幅(%)','金额(亿)']

    indexes = ['000001.SH', # 上证指数
               '399001.SZ', # 深证成指
               '399006.SZ', # 创业板指
               '399005.SZ'  # 中小板指
              ]


    def __init__(self, eventEngine, name=None):
        super().__init__(None, True, False)

        self._eventEngine = eventEngine
        self._name = name
        self._filter = DyStockMarketFilter(DyStockMarketIndexMonitorWidget.indexes)# 创建一个返回四大指数的filter
        self._latestTickTime = None# 最新tick事件
        self._latestFreq = 'N/A'
        
        self.setColNames(DyStockMarketIndexMonitorWidget.header)
        self.setAutoForegroundCol('涨幅(%)')# 根据涨幅来设置这一行的颜色
        
        self._registerEvent()

    def _stockMarketTicksHandler(self, event):
        ticks = self._filter.filter(event.data)# 返回四大指数

        # update UI table
        for code, tickData in ticks.items():
            rowData = [tickData.name,
                       tickData.price,
                       (tickData.price - tickData.preClose)*100/tickData.preClose,
                       tickData.amount/10**8# 单位是亿
                      ]

            self[code] = rowData# 直接更新，根据KV更新

        # get latest index tick
        shTickData = ticks.get(DyStockCommon.shIndex)# 上证指数
        szTickData = ticks.get(DyStockCommon.szIndex)# 深圳指数
        
        if shTickData is not None and szTickData is not None:
            tickData = shTickData if shTickData.time > szTickData.time else szTickData# 哪个时间晚，用谁的
        elif shTickData is not None:
            tickData = shTickData
        else:
            tickData = szTickData

        if tickData is None:
            return

        # 更新频率, 计算新浪更新数据的频率
        if self._latestTickTime is not None and tickData.time > self._latestTickTime:
            self._latestFreq = DyStockCommon.getTimeInterval(self._latestTickTime, tickData.time)# 获取时间差（s）

        title = '{0}[{1}], 频率{2}s'.format(self.parentWidget().windowTitle()[:4], tickData.datetime.strftime('%Y-%m-%d %H:%M:%S'), self._latestFreq)
        self.parentWidget().setWindowTitle(title)

        self._latestTickTime = tickData.time
    # 这也是通过股票市场行情TICK实时更新的
    def _registerEvent(self):
        self.signal.connect(self._stockMarketTicksHandler)
        self._eventEngine.register(DyEventType.stockMarketTicks, self.signal.emit)
