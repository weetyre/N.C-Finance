from collections import OrderedDict

from DyCommon.Ui.DyTableWidget import *
from EventEngine.DyEvent import *

#一个表格
class DyStockSelectStrategyParamWidget(DyTableWidget):

    def __init__(self):
        super().__init__(None, False, False, False, False)
    #设置表格的参数（列名）
    def set(self, paramters):
        """ @paramters: ordered dict """
        if paramters is None:
            return

        header = list(paramters)
        self.setColNames(header)

        self[0] = [x if x is None or isinstance(x, str) or isinstance(x, int) or isinstance(x, float) else str(x) for x in paramters.values()]

        for i, name in enumerate(header):
            if '权重' in name:
                self.setItemBackground(0, i, Qt.yellow)
                self.setItemForeground(0, i, Qt.black)
    #得到表格的参数
    def get(self):
        colNbr = self.columnCount()
        param = OrderedDict()

        for i in range(colNbr):
            key = self.horizontalHeaderItem(i).text()
            value = self[0, i]

            param[key] = value

        return param
    #鼠标悬浮设置提示
    def setToolTip(self, tooltips=None):
        if tooltips is None:
            return

        for name, text in tooltips.items():
            pos = self._getColPos(name)
            item = self.horizontalHeaderItem(pos)
            item.setToolTip(text)
