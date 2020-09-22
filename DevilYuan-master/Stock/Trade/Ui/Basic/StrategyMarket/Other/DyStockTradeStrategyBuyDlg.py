from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QApplication, QTextEdit, QMessageBox
from PyQt5 import QtCore

from Stock.Common.DyStockCommon import *
from EventEngine.DyEvent import *
from DyCommon.Ui.DyTableWidget import *

# 股票实盘策略买对话框
class DyStockTradeStrategyBuyDlg(QDialog):

    stockMarketTicksSignal = QtCore.pyqtSignal(type(DyEvent()))# 更新表格的
    stockStrategyMonitoredCodesAckSignal = QtCore.pyqtSignal(type(DyEvent()))#  # 策略手动买入相关事件，主要为了测试用

    def __init__(self, eventEngine, strategyCls):
        super().__init__()

        self._eventEngine = eventEngine
        self._strategyCls = strategyCls

        self._code = None # current stock code
        self._tick = None # current tick of @self._code
        self._monitoredCodes = None

        self._initUi()

        self._registerEvent()

        self._init()# 请求在其他地方已经注册过了，这里这负责put，或者注册ACK
    # 主要是传入策略类
    def _init(self):# 初始化这个之后，就会发送当前策略监控的股票
        event = DyEvent(DyEventType.stockStrategyMonitoredCodesReq)#  请求策略监控股票池代码事件，因为买要看监控
        event.data = self._strategyCls

        self._eventEngine.put(event)

    def _initUi(self):
        self.setWindowTitle(self._strategyCls.chName)# 策略中文名
        
        # 监控池
        monitoredCodesLabel = QLabel('策略监控股票池里的股票代码')
        monitoredCodesLabel.setStyleSheet("color:#4169E1")

        self._monitoredCodesTextEdit = QTextEdit()
        self._monitoredCodesTextEdit.setReadOnly(True)

        # 买入
        buyCodeLabel = QLabel('股票代码')
        buyCodeLabel.setStyleSheet("color:#4169E1")
        self._buyCodeLineEdit = QLineEdit()

        buyVolumeLabel = QLabel('数量(手)')
        buyVolumeLabel.setStyleSheet("color:#4169E1")
        self._buyVolumeLineEdit = QLineEdit('1')

        buyPriceLabel = QLabel('价格(元)')
        buyPriceLabel.setStyleSheet("color:#4169E1")
        self._buyPriceLineEdit = QLineEdit()

        # 行情
        self._codeLabel = QLabel('股票代码')
        self._nameLabel = QLabel('股票名称')
        self._priceLabel = QLabel('股票现价')
        self._increaseLabel = QLabel('涨幅(%):')

        self._bidAskTable = DyTableWidget(readOnly=True, index=False, floatRound=3)# 不适用索引，保留三位小数
        self._bidAskTable.setColNames([None, '价格(元)', '数量(手)'])
        self._bidAskTable.fastAppendRows([
                                            ['卖5', None, None],
                                            ['卖4', None, None],
                                            ['卖3', None, None],
                                            ['卖2', None, None],
                                            ['卖1', None, None],
                                            [None, None, None],
                                            ['买1', None, None],
                                            ['买2', None, None],
                                            ['买3', None, None],
                                            ['买4', None, None],
                                            ['买5', None, None]
                                        ])

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('买入')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(monitoredCodesLabel, 0, 0)
        grid.addWidget(self._monitoredCodesTextEdit, 1, 0, 10, 10)

        start = 12

        grid.addWidget(buyCodeLabel, start + 0, 0)
        grid.addWidget(self._buyCodeLineEdit, start + 1, 0)
        grid.addWidget(buyVolumeLabel, start + 2, 0)
        grid.addWidget(self._buyVolumeLineEdit, start + 3, 0)
        grid.addWidget(buyPriceLabel, start + 4, 0)
        grid.addWidget(self._buyPriceLineEdit, start + 5, 0)

        grid.addWidget(self._codeLabel, start + 0, 1, 1, 10)
        grid.addWidget(self._nameLabel, start + 1, 1)
        grid.addWidget(self._priceLabel, start + 2, 1)
        grid.addWidget(self._increaseLabel, start + 3, 1)
        grid.addWidget(self._bidAskTable, start + 4, 1, 30, 10)

        grid.addWidget(okPushButton, start + 6, 0)
        grid.addWidget(cancelPushButton, start + 7, 0)
 
 
        self.setLayout(grid)
        self.setMinimumWidth(QApplication.desktop().size().width()//5)


        self._buyCodeLineEdit.textChanged.connect(self._buyCodeChanged)# 买入代码发生变化
    # ok处理函数
    def _ok(self):
        try:
            if self._codeLabel.text() != self._tick.code:
                QMessageBox.warning(self, '错误', '没有指定代码的Tick数据!')
                return
        except Exception:
            QMessageBox.warning(self, '错误', '没有指定代码的Tick数据!')
            return

        event = DyEvent(DyEventType.stockStrategyManualBuy)# 策略手动买入事件，也就是说通过UI买入
        event.data['class'] = self._strategyCls
        event.data['tick'] = self._tick
        event.data['volume'] = float(self._buyVolumeLineEdit.text()) * 100# 数量为手，所以乘个100

        # 不指定价格，则根据tick买入
        price = self._buyPriceLineEdit.text()# 买入价格
        event.data['price'] = float(price) if price else None

        self._eventEngine.put(event)
        # 买完之后，就解除注册事件
        self._unregisterEvent()

        self.accept()
    # 取消
    def _cancel(self):
        self._unregisterEvent()

        self.reject()
    # 获取输入股票代码
    def _getInputCode(self):
        if not self._monitoredCodes:
            return None

        code = self._buyCodeLineEdit.text()
        if len(code) != 6:
            return None

        code = DyStockCommon.getDyStockCode(code)
        if code not in self._monitoredCodes:
            return None

        return code
    # 买入股票代码变化，必须在监控的股票里
    def _buyCodeChanged(self):
        self._code = self._getInputCode()
        if self._code is None:
            self._codeLabel.setText('输入代码在策略监控股票池里不存在!')
            return

        self._codeLabel.setText(self._code)
    #
    def _stockStrategyMonitoredCodesAckSignalEmitWrapper(self, event):
        self.stockStrategyMonitoredCodesAckSignal.emit(event)
    #
    def _stockMarketTicksSignalEmitWrapper(self, event):
        self.stockMarketTicksSignal.emit(event)
    # 注册事件
    def _registerEvent(self):
        self.stockMarketTicksSignal.connect(self._stockMarketTicksHandler)# 股票池行情的Tick事件, 包含指数
        self._eventEngine.register(DyEventType.stockMarketTicks, self._stockMarketTicksSignalEmitWrapper)
        #  策略手动买入相关事件，主要为了测试用
        self.stockStrategyMonitoredCodesAckSignal.connect(self._stockStrategyMonitoredCodesAckHandler)
        self._eventEngine.register(DyEventType.stockStrategyMonitoredCodesAck, self._stockStrategyMonitoredCodesAckSignalEmitWrapper)
    # 接注册两个事件
    def _unregisterEvent(self):
        self.stockMarketTicksSignal.disconnect(self._stockMarketTicksHandler)
        self._eventEngine.unregister(DyEventType.stockMarketTicks, self._stockMarketTicksSignalEmitWrapper)

        self.stockStrategyMonitoredCodesAckSignal.disconnect(self._stockStrategyMonitoredCodesAckHandler)
        self._eventEngine.unregister(DyEventType.stockStrategyMonitoredCodesAck, self._stockStrategyMonitoredCodesAckSignalEmitWrapper)
    # 最终把股票策略监控的股票显示，在窗口开的时候，就会执行这个函数
    def _stockStrategyMonitoredCodesAckHandler(self, event):
        codes = event.data

        self._monitoredCodes = codes # 并赋值监控股票
        self._monitoredCodesTextEdit.setText(str(codes))
    #  股票池行情的Tick事件函数, 包含指数，主要更新现在的窗口，窗口开着就会一直更新，是通过过一个timer事件引擎所控制
    def _stockMarketTicksHandler(self, event):
        ticks = event.data

        self._tick = ticks.get(self._code)# 现在的股票代码，设置tick实例
        if self._tick is None:
            return

        tick = self._tick

        self._codeLabel.setText(tick.code)
        self._nameLabel.setText(tick.name)

        self._priceLabel.setText(str(tick.price))
        if tick.price > tick.preClose:# 他是涨的
            self._priceLabel.setStyleSheet("color:red")
        elif tick.price < tick.preClose:# 他是跌的
            self._priceLabel.setStyleSheet("color:darkgreen")
        # 涨幅计算
        increase = round((tick.price - tick.preClose)/tick.preClose*100, 2)
        self._increaseLabel.setText('涨幅(%): {0}%'.format(increase))
        if increase > 0:
            self._increaseLabel.setStyleSheet("color:red")# 设置对应的颜色
        elif increase < 0:
            self._increaseLabel.setStyleSheet("color:darkgreen")

        self._bidAskTable.fastAppendRows([
                                            ['卖5', tick.askPrices[4], round(tick.askVolumes[4]/100)],# 数量转化为手
                                            ['卖4', tick.askPrices[3], round(tick.askVolumes[3]/100)],
                                            ['卖3', tick.askPrices[2], round(tick.askVolumes[2]/100)],
                                            ['卖2', tick.askPrices[1], round(tick.askVolumes[1]/100)],
                                            ['卖1', tick.askPrices[0], round(tick.askVolumes[0]/100)],
                                            [None, tick.price, None],
                                            ['买1', tick.bidPrices[0], round(tick.bidVolumes[0]/100)],
                                            ['买2', tick.bidPrices[1], round(tick.bidVolumes[1]/100)],
                                            ['买3', tick.bidPrices[2], round(tick.bidVolumes[2]/100)],
                                            ['买4', tick.bidPrices[3], round(tick.bidVolumes[3]/100)],
                                            ['买5', tick.bidPrices[4], round(tick.bidVolumes[4]/100)]
                                        ], new=True)# 新加入

