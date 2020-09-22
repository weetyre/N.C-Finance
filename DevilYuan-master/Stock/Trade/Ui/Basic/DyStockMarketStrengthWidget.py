from PyQt5 import QtCore

from DyCommon.Ui.DyTableWidget import *
from EventEngine.DyEvent import *
from ....Common.DyStockCommon import *

# 市场强度
class DyStockMarketStrengthWidget(DyTableWidget):

    signal = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self, eventEngine, name=None):
        super().__init__(None, True, False)

        self.setColNames(['', ''])# 没有列名
        self.horizontalHeader().setVisible(False)

        self._eventEngine = eventEngine
        self._name = name

        self._initUi()
        
        self._registerEvent()
    # 这里是每一行的数据
    def _initUi(self):
        rows = [['当前', None],
                ['开盘', None],
                ['MAX', None],
                ['强中弱占比', None]]

        self.fastAppendRows(rows, new=True)# 然后添加新行
    # 设置强度前景色
    def _setColor(self, strategyCls, row, strength):
        if strength is None:
            return

        strength = round(strength, 2)

        if strength > strategyCls.marketStrengthMiddleUpper:# 市场强度上限
            color = Qt.red
        elif strength < strategyCls.marketStrengthMiddleLower:# 市场强度下限
            color = Qt.darkGreen
        else:
            color = QColor("#4169E1")

        self.item(row, 1).setForeground(color)# 第二列
    # 市场强度，强中弱，算成比例
    def _getRatioItem(self, strongCount, middleCount, weakCount):
        ratioSum = strongCount + middleCount + weakCount

        strongRatio = round(strongCount/ratioSum*100, 2)
        middleRatio = round(middleCount/ratioSum*100, 2)
        weakRatio = round(weakCount/ratioSum*100, 2)

        ratioItem = '{0}%, {1}%, {2}%'.format(strongRatio, middleRatio, weakRatio)

        return ratioItem
    # 从策略获得数据之后且UI 更新后，紧接着发送到WX端口更新
    def _putEvent(self, rows):
        event = DyEvent(DyEventType.stockMarketStrengthUpdateFromUi)
        event.data = rows

        self._eventEngine.put(event)
    # 来自策略的市场强度更新事件（添加到UI）
    def _stockMarketStrengthUpdateHandler(self, event):
        strategyCls = event.data['class']
        time = event.data['time']
        strengthInfo = event.data['data']

        maxItem = '{0}, {1}'.format(round(strengthInfo.max, 2), strengthInfo.maxTime)
        ratioItem = self._getRatioItem(strengthInfo.strongCount, strengthInfo.middleCount, strengthInfo.weakCount)

        rows = [['当前', round(strengthInfo.cur, 2)],
                ['开盘', None if strengthInfo.open is None else round(strengthInfo.open, 2)],
                ['MAX', maxItem],
                ['强中弱[总]', ratioItem]]

        # rolling counts 最近多少tick
        for tickNbr, (deltaTime, strongCount, middleCount, weakCount) in strengthInfo.rollingCounts.items():
            ratioItem = self._getRatioItem(strongCount, middleCount, weakCount)

            rows.append(['强中弱[{0}T({1})]'.format(tickNbr, deltaTime), ratioItem])

        self.fastAppendRows(rows, new=True)# 添加新数据

        # set color，123行标准行
        self._setColor(strategyCls, 0, strengthInfo.cur)# 现在
        self._setColor(strategyCls, 1, strengthInfo.open)# 开始
        self._setColor(strategyCls, 2, strengthInfo.max)# 最高
        # 设置窗口大小
        self.parentWidget().setWindowTitle('{0}[{1}]'.format(self.parentWidget().windowTitle()[:4], time))

        # put event
        self._putEvent(rows)
    # 注册来自策略的市场强度更新事件
    def _registerEvent(self):
        self.signal.connect(self._stockMarketStrengthUpdateHandler)
        self._eventEngine.register(DyEventType.stockMarketStrengthUpdate, self.signal.emit)
