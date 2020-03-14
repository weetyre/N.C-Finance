from DyCommon.Ui.DyTreeWidget import *

from EventEngine.DyEvent import *
from ....Trade.Ui.Basic.DyStockTradeStrategyWidget import * 
from ....Select.Ui.Basic.DyStockSelectStrategyWidget import *

#这个继承选择策略那个类（具有获取策略类以及对应参数的功能）
class DyStockBackTestingStrategyWidget(DyStockSelectStrategyWidget):
    """ 只能选中一个策略回测 """

    def __init__(self, paramWidget=None):
        self.__class__.strategyFields = DyStockTradeStrategyWidget.strategyFields #返回的是所有策略类
        super().__init__(paramWidget)
