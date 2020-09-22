from EventEngine.DyEventEngine import *
from ..DyStockSelectCommon import *
from DyCommon.DyCommon import *
from .DyStockSelectSelectEngine import *
from .Regression.DyStockSelectRegressionEngine import *
from ...Data.Viewer.DyStockDataViewer import *
from .DyStockSelectViewerEngine import *


class DyStockSelectMainEngine(object):

    def __init__(self):
        self._eventEngine = DyEventEngine(DyStockSelectEventHandType.nbr, False)# 每一个大功能下都会开一个多事件引擎，并且指定线程数，这个为3，不需要timer
        self._info = DyInfo(self._eventEngine)

        self._selectEngine = DyStockSelectSelectEngine(self._eventEngine, self._info)
        self._regressionEngine = DyStockSelectRegressionEngine(self._eventEngine, self._info)
        self._viewerEngine = DyStockSelectViewerEngine(self._eventEngine, self._info)

        self._initDataViewer()

        self._eventEngine.start()# 开始

    @property
    def eventEngine(self):
        return self._eventEngine

    @property
    def info(self):
        return self._info

    def exit(self):
        pass
    # 这是为了方便写的一个数据查看
    def _initDataViewer(self):
        errorInfo = DyErrorInfo(self._eventEngine)
        dataEngine = DyStockDataEngine(self._eventEngine, errorInfo, False)
        self._dataViewer = DyStockDataViewer(dataEngine, errorInfo)

    @property
    def dataViewer(self):
        return self._dataViewer
