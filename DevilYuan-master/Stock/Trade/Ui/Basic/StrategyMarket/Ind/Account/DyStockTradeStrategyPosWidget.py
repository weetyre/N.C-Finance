import copy
from PyQt5 import QtCore

from DyCommon.Ui.DyTableWidget import *

# 交易策略持仓窗口
class DyStockTradeStrategyPosWidget(DyTableWidget):
    """ 策略持仓窗口 """

    stockMarketTicksSignal = QtCore.pyqtSignal(type(DyEvent()))

    header = ['代码', '名称', '总数量/可用数量(股)', '成本价(元)', '现价(元)', '市值(元)', '盈亏(元)', '盈亏比(%)', '除权除息', '建仓时间']


    def __init__(self, eventEngine, strategyCls):
        super().__init__(readOnly=True, index=False, floatRound=3)# 不适用ORG列

        self._eventEngine = eventEngine
        self._strategyCls = strategyCls

        self.setColNames(self.header)
        self.setAutoForegroundCol('盈亏(元)')

        self._curPos = {}# 当前持仓
    # 更新持仓（一支一支更新）（UI）
    def _updatePos(self, pos):
        datetime_ = pos.datetime
        try:
            datetime_ = pos.datetime.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass

        self[pos.code] = [pos.code, pos.name,
                      '%.3f/%.3f'%(pos.totalVolume, pos.availVolume),
                       pos.cost, pos.price,
                       pos.totalVolume*pos.price,
                       pos.totalVolume*(pos.price - pos.cost),
                       (pos.price - pos.cost)/pos.cost*100 if pos.cost > 0 else 'N/A',
                       '是' if pos.xrd else '否',
                       datetime_
                       ]# 直接就会更具KV更新了，这个只是更新，也可以加
    # 策略持仓更新
    def update(self, positions):
        """
            @positions: OrderedDict or dict, {code: DyStockPos}。持仓是全推，不是增量式推送。
        """
        self.clearAllRows()# 持仓是全推

        for _, pos in positions.items():
            self._updatePos(pos)# UI
        
        # register/unregister event or not
        if not self._curPos and positions:
            self._registerEvent()# 更新当前UI持仓，就更新当前价格
        elif self._curPos and not positions:
            self._unregisterEvent()

        self._curPos = copy.deepcopy(positions)
    # 解除注册
    def closeEvent(self, event):
        if self._curPos:
            self._unregisterEvent()

        return super().closeEvent(event)

    def _stockMarketTicksSignalEmitWrapper(self, event):
        self.stockMarketTicksSignal.emit(event)
    # 注册股票池行情的Tick事件, 包含指数
    def _registerEvent(self):
        self.stockMarketTicksSignal.connect(self._stockMarketTicksHandler)
        self._eventEngine.register(DyEventType.stockMarketTicks, self._stockMarketTicksSignalEmitWrapper)
    # 解注册
    def _unregisterEvent(self):
        self.stockMarketTicksSignal.disconnect(self._stockMarketTicksHandler)
        self._eventEngine.unregister(DyEventType.stockMarketTicks, self._stockMarketTicksSignalEmitWrapper)
    #
    def _stockMarketTicksHandler(self, event):
        ticks = event.data

        for code, pos in self._curPos.items():
            tick = ticks.get(code)
            if tick is None:
                continue

            pos.price = tick.price

            self._updatePos(pos)# UI 更新


