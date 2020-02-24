from datetime import *
from collections import OrderedDict

from PyQt5.QtWidgets import QComboBox, QCheckBox, QGridLayout, QLabel, QLineEdit, QPushButton, QDialog, QApplication

from DyCommon.Ui.DyTableWidget import *

#回测设置窗口
class DyStockBackTestingSettingDlg(QDialog):
    #默认设置
    settings = \
        {
            '止损':
                OrderedDict\
                    ([
                        ('无', None),
                        ('固定', [['盈利(%)'], [-5]]),
                        ('均线', [['低于几日均线'], [20]]),
                        ('阶梯', [['初始止损比例', '阶梯长度', '阶梯变化率'], [0.9, 0.1, 0.09]]),
                        ('策略', None),
                    ]),

            '止盈':
                OrderedDict\
                    ([
                        ('无', None),
                        ('固定', [['盈利(%)'], [5]]),
                        ('均线', [['低于几日均线'], [5]]),
                        ('策略', None),
                    ]),

            '止时':
                OrderedDict\
                    ([
                        ('无', None),
                        ('固定', [['持有期', '盈利(%)'], [4, 2]]),
                        ('策略', None),
                    ])
        }

    def __init__(self, data):
        super().__init__()

        self._data = data

        self._initUi()

        self._initStopLossUi()
        self._initStopProfitUi()
        self._initStopTimeUi()

    def _initUi(self):
        self.setWindowTitle('回测设置')

        cashLabel = QLabel('初始资金(元)')
        cashLabel.setStyleSheet("color:#4169E1")
        self._cashLineEdit = QLineEdit('1000000')

        riskGuardLabel = QLabel('风控守护值(日)')
        riskGuardLabel.setStyleSheet("color:#4169E1")
        self._riskGuardLineEdit = QLineEdit('0')
        self._riskGuardLineEdit.setToolTip('清仓后多少交易日禁止买入, 0: 不启动风控守护')

        slippageLabel = QLabel('滑点(‰)')
        slippageLabel.setStyleSheet("color:#4169E1")
        self._slippageLineEdit = QLineEdit('0')

        stopLossLabel = QLabel('止损')
        stopLossLabel.setStyleSheet("color:darkgreen")
        self._stopLossCls = QComboBox()
        self._stopLossParam = DyTableWidget(index=False)

        stopProfitLabel = QLabel('止盈')
        stopProfitLabel.setStyleSheet("color:red")
        self._stopProfitCls = QComboBox()
        self._stopProfitParam = DyTableWidget(index=False)

        stopTimeLabel = QLabel('止时')
        stopTimeLabel.setStyleSheet("color:#4169E1")
        self._stopTimeCls = QComboBox()
        self._stopTimeParam = DyTableWidget(index=False)

        startDateLable = QLabel('开始日期')
        startDateLable.setStyleSheet("color:#4169E1")
        self._startDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        endDateLable = QLabel('结束日期')
        endDateLable.setStyleSheet("color:#4169E1")
        self._endDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        # DB Cache
        self._dbCacheCheckBox = QCheckBox('数据库缓存')
        self._dbCacheCheckBox.setChecked(False)
        self._dbCacheCheckBox.clicked.connect(self._dbCacheCheckBoxClicked)

        self._dbCachePreLoadDaysSizeLabel = QLabel('预载入日线数据大小(0: 回测周期)')
        self._dbCachePreLoadDaysSizeLabel.setEnabled(False)

        self._dbCachePreLoadDaysSizeLineEdit = QLineEdit('0')
        self._dbCachePreLoadDaysSizeLineEdit.setEnabled(False)

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        grid = QGridLayout()
        grid.addWidget(stopLossLabel, 0, 0)
        grid.addWidget(self._stopLossCls, 1, 0)
        grid.addWidget(self._stopLossParam, 1, 1)

        grid.addWidget(stopProfitLabel, 2, 0)
        grid.addWidget(self._stopProfitCls, 3, 0)
        grid.addWidget(self._stopProfitParam, 3, 1)

        grid.addWidget(stopTimeLabel, 4, 0)
        grid.addWidget(self._stopTimeCls, 5, 0)
        grid.addWidget(self._stopTimeParam, 5, 1)

        grid.addWidget(cashLabel, 6, 0)
        grid.addWidget(self._cashLineEdit, 6, 1)

        grid.addWidget(riskGuardLabel, 7, 0)
        grid.addWidget(self._riskGuardLineEdit, 7, 1)

        grid.addWidget(slippageLabel, 8, 0)
        grid.addWidget(self._slippageLineEdit, 8, 1)

        dateStartPos = 9

        # date
        grid.addWidget(startDateLable, dateStartPos, 0)
        grid.addWidget(self._startDateLineEdit, dateStartPos + 1, 0)

        grid.addWidget(endDateLable, dateStartPos, 1)
        grid.addWidget(self._endDateLineEdit, dateStartPos + 1, 1)

        # DB cache
        grid.addWidget(self._dbCacheCheckBox, dateStartPos + 2, 0)
        grid.addWidget(self._dbCachePreLoadDaysSizeLabel, dateStartPos + 3, 0)
        grid.addWidget(self._dbCachePreLoadDaysSizeLineEdit, dateStartPos + 3, 1)

        # OK & Cancel
        grid.addWidget(okPushButton, dateStartPos + 4, 1)
        grid.addWidget(cancelPushButton, dateStartPos + 4, 0)

        self.setLayout(grid)

        self.resize(QApplication.desktop().size().width()//2, QApplication.desktop().size().height()//3)
    # 初始化止损UI
    def _initStopLossUi(self):
        self._stopLossCls.addItems(list(self.settings['止损'].keys()))

        self._stopLossCls.currentIndexChanged.connect(self._stopLossClsChange)

        self._stopLossCls.setCurrentText('无')
    # 如果更改了
    def _stopLossClsChange(self):
        text = self._stopLossCls.currentText()
        param = self.settings['止损'][text]
        
        self._setParam(self._stopLossParam, param)#同时传入
    # 初始化
    def _initStopProfitUi(self):
        self._stopProfitCls.addItems(list(self.settings['止盈'].keys()))

        self._stopProfitCls.currentIndexChanged.connect(self._stopProfitClsChange)

        self._stopProfitCls.setCurrentText('无')
    # 如果更改
    def _stopProfitClsChange(self):
        text = self._stopProfitCls.currentText()
        param = self.settings['止盈'][text]
        
        self._setParam(self._stopProfitParam, param)
    # 初始化， 如果更改
    def _initStopTimeUi(self):
        self._stopTimeCls.addItems(list(self.settings['止时'].keys()))

        self._stopTimeCls.currentIndexChanged.connect(self._stopTimeClsChange)

        self._stopTimeCls.setCurrentText('无')

    def _stopTimeClsChange(self):
        text = self._stopTimeCls.currentText()
        param = self.settings['止时'][text]
        
        self._setParam(self._stopTimeParam, param)
    # 设置参数
    def _setParam(self, table, param):
        if param is None:# 如果选择的是无
            table.setRowCount(0)
            table.setColumnCount(0)
            table.setEnabled(False)
            return

        table.setEnabled(True)

        table.setColNames(param[0])
        table.appendRow(param[1], new=True)#加一行
    #获得参数
    def _getParam(self, table):
        colNbr = table.columnCount()
        param = []

        for i in range(colNbr):
            key = table.horizontalHeaderItem(i).text()
            value = float(table[0, i])

            param.append(value)

        return param 
    # 数据库缓存打开了，就可以编辑了
    def _dbCacheCheckBoxClicked(self):
        enable = self._dbCacheCheckBox.isChecked()
        self._dbCachePreLoadDaysSizeLabel.setEnabled(enable)
        self._dbCachePreLoadDaysSizeLineEdit.setEnabled(enable)

    def _ok(self):
        self._data['startDate'] = self._startDateLineEdit.text()
        self._data['endDate'] = self._endDateLineEdit.text()

        self._data['cash'] = int(self._cashLineEdit.text())

        self._data['stopSettings'] = {}
        self._data['stopSettings']['stopLoss'] = [self._stopLossCls.currentText(), self._getParam(self._stopLossParam)]
        self._data['stopSettings']['stopProfit'] = [self._stopProfitCls.currentText(), self._getParam(self._stopProfitParam)]
        self._data['stopSettings']['stopTime'] = [self._stopTimeCls.currentText(), self._getParam(self._stopTimeParam)]

        self._data['riskGuard'] = int(self._riskGuardLineEdit.text())
        self._data['slippage'] = float(self._slippageLineEdit.text())

        if self._dbCacheCheckBox.isChecked():
            self._data['dbCachePreLoadDaysSize'] = int(self._dbCachePreLoadDaysSizeLineEdit.text())

        self.accept()

    def _cancel(self):
        self.reject()



