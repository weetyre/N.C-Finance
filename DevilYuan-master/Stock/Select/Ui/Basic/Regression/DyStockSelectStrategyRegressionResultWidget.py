
from PyQt5.QtWidgets import QTabWidget, QApplication

from .DyStockSelectStrategyRegressionPeriodResultWidget import *
from ....DyStockSelectCommon import *

# 具体的回归结果窗口
class DyStockSelectStrategyRegressionResultWidget(QTabWidget):

    def __init__(self, eventEngine, strategyCls, paramWidget=None):
        super().__init__()

        self._eventEngine = eventEngine
        self._strategyCls = strategyCls
        self._paramWidget = paramWidget

        # 每个回归策略会被分成几个时间周期并行运行，每个周期的回归结果会生成一个table窗口
        self._strategyPeriodWidgets = {} # 这是一个子周期tab窗口

        self._windows = [] # only for show window

    def _getTabPos(self, period):
        periodStartDates = [period[0]]

        for periodKey in self._strategyPeriodWidgets:
            periodStartDates.append(periodKey[1: 1+len('2016-01-01')])

        periodStartDates.sort()

        return periodStartDates.index(period[0])
    # 添加一个周期Tab
    def addTab(self, tabName, widget):
        self._strategyPeriodWidgets[tabName] = widget

        super().addTab(widget, tabName)
    # 这个就是添加一个回归周期的回归结果
    def append(self, period, day, result):
        """ 添加策略一个回归周期的回归结果 """

        # tab window title
        tabName = '[' + ','.join(period) + ']'

        if tabName not in self._strategyPeriodWidgets:
            widget = DyStockSelectStrategyRegressionPeriodResultWidget(self._eventEngine, tabName, self._strategyCls, self._paramWidget)
            widget.setColNames(result[0])# 设置列名
            
            tabPos = self._getTabPos(period)# 获得tab位置
            self.insertTab(tabPos, widget, tabName)# 插入tab

            # save
            self._strategyPeriodWidgets[tabName] = widget

        self._strategyPeriodWidgets[tabName].append(day, result[1:])# 基准日期，以及结果行添加

        self.parentWidget().raise_()
    # 移除所有的周期窗口
    def removeAll(self):
        count = self.count()

        for _ in range(count):
            self.removeTab(0)

        self._strategyPeriodWidgets = {}
    # 描述统计
    def describe(self):

        periodDfs = []
        for _, periodWidget in self._strategyPeriodWidgets.items():
            periodDf = periodWidget.getNumberDataFrame()
            if periodDf is not None:
                periodDfs.append(periodDf)

        df = pd.concat(periodDfs)# 相同列的向下拼起来

        info = df.describe()

        DyDataFrameWindow('描述统计', info, self)# 新生成一个窗口
    # 描述散列图
    def scatterMatrix(self):

        periodDfs = []
        for _, periodWidget in self._strategyPeriodWidgets.items():
            periodDf = periodWidget.getNumberDataFrame()
            if periodDf is not None:
                periodDfs.append(periodDf)

        df = pd.concat(periodDfs)

        pd.scatter_matrix(df)
        plt.gcf().show()
    # 获取数字列名
    def getNumberColNames(self):
        for _, periodWidget in self._strategyPeriodWidgets.items():
            return periodWidget.getNumberColNames()

        return None
    # 获取列名
    def _getColNames(self):
        for _, periodWidget in self._strategyPeriodWidgets.items():
            return periodWidget.getColNames()

        return None
    # 概率分布，根据特定的列
    def probDistAct(self, colName):
        series = []
        for _, periodWidget in self._strategyPeriodWidgets.items():
            periodSeries = periodWidget.getNumberSeries(colName)
            if periodSeries is not None:
                series.append(periodSeries)

        series = pd.concat(series)

        series.hist(bins=100, alpha=0.5, color='r')
        plt.title(colName)

    # 合并周期plt.gcf().show()
    def mergePeriod(self, name):
        # get all rows by period sequence
        allRows = []
        autoColName = None
        # 从小到大排序
        periods = sorted(self._strategyPeriodWidgets)
        for period in periods:
            periodWidget = self._strategyPeriodWidgets[period]# 找到那个widget

            allRows.extend(periodWidget.getAll())
            autoColName = periodWidget.getAutoColName()# 自动前景列名，这里主要是根据涨幅走

        window = DyStockSelectStrategyRegressionResultWidget(self._eventEngine, self._strategyCls, self._paramWidget)
        tabName = '{0},{1}'.format(periods[0][:11], periods[-1][-11:])#周期

        widget = DyStockSelectStrategyRegressionPeriodResultWidget(self._eventEngine, tabName, self._strategyCls, self._paramWidget)

        # set column names with period widget's column names
        widget.rawSetColNames(self._getColNames())
            
        # append to new statistic table widget
        widget.rawAppend(allRows, autoColName)

        window.addTab(tabName, widget)

        # show window
        window.setWindowTitle(self._strategyCls.chName)
        window.setWindowFlags(Qt.Window)
        window.resize(QApplication.desktop().size().width()//2, QApplication.desktop().size().height()//2)
        window.show()# 一般都是先显示，然后在转去其他

        window.move((QApplication.desktop().size().width() - widget.width())//2, (QApplication.desktop().size().height() - widget.height())//2)

        self._windows.append(window)
