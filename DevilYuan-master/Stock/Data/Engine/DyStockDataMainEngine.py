from EventEngine.DyEventEngine import *
from .DyStockDataEngine import *
from ..DyStockDataCommon import *
from DyCommon.DyCommon import *


class DyStockDataMainEngine(object):
    """description of class"""

    def __init__(self):
        self._eventEngine = DyEventEngine(DyStockDataEventHandType.nbr, False)#根据数据类型创建不同线程数目得引擎
        self._info = DyInfo(self._eventEngine)

        self._dataEngine = DyStockDataEngine(self._eventEngine, self._info)

        self._eventEngine.start()#开始事件引擎
    #以下的方法直接返回属性（名字和实例属性相仿）
    @property
    def eventEngine(self):
        return self._eventEngine

    @property
    def info(self):
        return self._info

    @property
    def dataEngine(self):
        return self._dataEngine

    def exit(self):
        pass