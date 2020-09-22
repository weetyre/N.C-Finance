from collections import OrderedDict

from DyCommon.Ui.DyTableWidget import *


class DyStockTradeStrategyMarketMonitorDataWidget(DyTableWidget):
    """ 股票实盘策略数据窗口 """

    # 克隆数据
    class LogData:
        """
            log-structured storage for clone
        """
        def __init__(self):
            self.newData = None
            self.updatedData = OrderedDict() # {row key: row}

        def init(self, data):
            self.newData = data
            self.updatedData = OrderedDict()

        def update(self, data):
            for row in data:
                code = row[0] # pos 0 is code, date or something else, but should be key for one row
                self.updatedData[code] = row

    # 初始化
    def __init__(self, strategyCls, parent):
        super().__init__(None, True, False)

        self._strategyCls = strategyCls
        self._parent = parent

        self._logData = self.LogData() # for clone
        # 设置列名，设置自动前景色
        self.setColNames(strategyCls.dataHeader)
        self.setAutoForegroundCol('涨幅(%)')
    # 更新数据到窗口
    def update(self, data, newData=False):
        """ @data: [[col0, col1, ...]] """

        if newData: # !!!new, without considering keys
            self.fastAppendRows(data, autoForegroundColName='涨幅(%)', new=True)

            self._logData.init(data)# 初始化，变成newdata
        else: # updating by keys
            rowKeys = []
            for row in data:
                code = row[0] # pos 0 is code, date or something else, but should be key for one row
                self[code] = row# 在这已经设置

                rowKeys.append(code)

            self.setItemsForeground(rowKeys, (('买入', Qt.red), ('卖出', Qt.darkGreen)))# 为了设置前景色

            self._logData.update(data)# 如果不是新数据的话，执行跟新

    def clone(self):
        self_ = self.__class__(self._strategyCls, self._parent)

        # new data
        if self._logData.newData is not None:
            self_.update(self._logData.newData, newData=True)

        # data with keys
        data = [row for _, row in self._logData.updatedData.items()]
        if data:
            self_.update(data, newData=False)

        return self_

    def closeEvent(self, event):
        self._parent.removeCloneDataWidget(self)

        return super().closeEvent(event)
