from DyCommon.Ui.DyTableWidget import *

# 策略委托窗口，不是当日委托是策略启动后的委托
class DyStockTradeStrategyEntrustsWidget(DyTableWidget):
    """ 策略委托窗口，不是当日委托是策略启动后的委托 """

    header = ['DY委托号', '券商委托号', '委托时间', '代码', '名称', '类型', '委托价(元)', '委托数量(股)', '成交数量(股)', '状态']

    def __init__(self):
        super().__init__(readOnly=True, index=True, floatRound=3)

        self.setColNames(self.header)
    # 更新新的委托，加一行
    def update(self, entrusts):
        """
            @entrusts: OrderedDict or dict only with one entrust. {dyEntrustId: DyStockEntrust}
        """
        rowKeys = []
        for dyEntrustId, entrust in entrusts.items():
            self[dyEntrustId] = [entrust.dyEntrustId, entrust.brokerEntrustId,
                                 entrust.entrustDatetime.strftime('%Y-%m-%d %H:%M:%S'),
                                 entrust.code, entrust.name,
                                 entrust.type,
                                 entrust.price,
                                 int(entrust.totalVolume), int(entrust.dealedVolume),
                                 entrust.status
                                 ]# 这个只是更新，一支一支的更新，也可以加

            rowKeys.append(dyEntrustId)

        self.setItemsForeground(rowKeys, (('买入', Qt.red), ('卖出', Qt.darkGreen)))# 这两个字段设置前景色