from ....Strategy.DyStockSelectStrategyTemplate import *
from .....Common.Ui.Basic.DyStockTableWidget import *

# 这有时每一个小的周期回归结果，父类是操作结果表，给结果表一些基本的操作
class DyStockSelectStrategyRegressionPeriodResultWidget(DyStockTableWidget):

    def __init__(self, eventEngine, name, strategyCls, paramWidget=None):
        self._strategyCls = strategyCls

        super().__init__(eventEngine, name=name, index=True)

        self._paramWidget = paramWidget
    #
    def _initHeaderMenu(self):
        super()._initHeaderMenu()

        self._headerMenu.addSeparator()

        # 策略相关菜单
        menu = self._headerMenu.addMenu('策略相关')

        action = QAction('贝叶斯统计', self)
        action.triggered.connect(self._bayesianStatsAct)
        menu.addAction(action)
        action.setEnabled(hasattr(self._strategyCls, 'bayesianStats'))
    # 添加行，在这里调用，最终添加行成功（彻底结束）
    def append(self, date, rows):
        for i, row in enumerate(rows):
            if i == 0:
                row.insert(0, date)# 基准日期，以及前面的 * 符号，每到一个新的基准日期加*
                row.insert(0, '*')
            else:
                row.insert(0, date)# 如果一直在开头插入的话，他会自动后调
                row.insert(0, '')

        self.fastAppendRows(rows, DyStockSelectStrategyTemplate.getAutoColName())#返回当日涨幅 快速插入行，必须要有header
    # 获得自动前景色列名
    def getAutoColName(self):
        return DyStockSelectStrategyTemplate.getAutoColName()
    #设置列名
    def setColNames(self, names):
        super().setColNames(['*', '基准日期'] + names)
    # 原始数据添加
    def rawAppend(self, rows, autoColName):
        self.fastAppendRows(rows, autoColName, True)
    # 原始设置列名
    def rawSetColNames(self, names):
        super().setColNames(names)
    # 获取基准日期以及代码
    def getDateCodeList(self):
        dateCodeList = self.getColumnsData(['基准日期', '代码'])# 指定列名获取所有值

        return dateCodeList
    # 获得目标代码日期比较标的
    def getTargetCodeDateN(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None: return None, None, None, None

        code = self[item.row(), '代码']
        baseDate = self[item.row(), '基准日期']

        param = self._widgetParam.get(self._strategyName)

        target = param['跟哪个标的比较']
        n = -param['向前N日周期']

        return target, code, baseDate, n
    # 获得目标代码日期
    def getRightClickCodeDate(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None: return None, None

        code = self[item.row(), '代码']
        baseDate = self[item.row(), '基准日期']

        return code, baseDate
    # 右键获取代码日期
    def getRightClickCodeName(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None: return None, None

        code = self[item.row(), '代码']
        name = self[item.row(), '名称']

        return code, name
    # 获取代码基准日期
    def getCodeDate(self, item):
        code = self[item.row(), '代码']
        baseDate = self[item.row(), '基准日期']

        return code, baseDate
    #
    def getUniqueName(self):
        """
            子类改写
        """
        return '{0}_{1}'.format(self._strategyCls.chName, self._name)
    # 获取自定义保存数据
    def getCustomSaveData(self):
        """
            子类改写
        """
        customData = {'class': 'DyStockSelectStrategyRegressionResultWidget',
                      'strategyCls': self._strategyCls.name
                      }

        return customData
    # 自己加一个窗口
    def _newWindow(self, rows=None):
        """
            子类改写
        """
        window = self.__class__(self._eventEngine, self._name, self._strategyCls, self._paramWidget)

        if rows is None:
            rows = self.getAll()

        window.rawSetColNames(self.getColNames())
        window.rawAppend(rows, self.getAutoForegroundColName())

        window.setWindowTitle('{0}{1}'.format(self._strategyCls.chName, self._name))
        window.showMaximized()

        self._windows.append(window)

    def _bayesianStatsAct(self):
        df = self.toDataFrame()

        df = self._strategyCls.bayesianStats(df, 1)

        # new window
        window = self.__class__(self._eventEngine, self._name, self._strategyCls, self._paramWidget)

        window.rawSetColNames(list(df.columns))
        window.rawAppend(df.values, self.getAutoForegroundColName())

        window.setWindowTitle('{0}{1}'.format(self._strategyCls.chName, self._name))
        window.showMaximized()

        self._windows.append(window)