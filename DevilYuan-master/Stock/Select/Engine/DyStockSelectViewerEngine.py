from EventEngine.DyEvent import *
from ...Data.Viewer.DyStockDataViewer import *
from ...Data.Viewer.DyStockDataWindow import *
from ...Data.Engine.DyStockDataEngine import *
from ..DyStockSelectCommon import *

# 股票选股绘图引擎
class DyStockSelectViewerEngine(object):
    
    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._testedStocks = None

        self._initDataViewer()

        self._registerEvent()

    def _initDataViewer(self):
        self._dataEngine = DyStockDataEngine(self._eventEngine, self._info, False)
        self._dataViewer = DyStockDataViewer(self._dataEngine, self._info) #  计算股票数据 生成matplotlib视图
        self._dataWindow = DyStockDataWindow(self._dataEngine, self._info)#  若要生成 跟股票代码相关 的 表格窗口 ，则需要使用DyStockDataWindow类

        # 省去非错误log的输出
        errorInfo = DyErrorInfo(self._eventEngine)# 只打错误和警告信息
        self._errorDataEngine = DyStockDataEngine(self._eventEngine, errorInfo, False)
    # 在这里注册绘图请求事件
    def _registerEvent(self):
        self._eventEngine.register(DyEventType.plotReq, self._plotReqHandler, DyStockSelectEventHandType.viewer)# 指定队列1运行
        self._eventEngine.register(DyEventType.stockSelectTestedCodes, self._stockSelectTestedCodesHandler, DyStockSelectEventHandType.viewer)# # 调试股票事件，指定队列1运行
    # 都会设置相应的调试股票代码
    def _stockSelectTestedCodesHandler(self, event):
        self._testedStocks = event.data

        self._dataViewer.setTestedStocks(self._testedStocks)
        self._dataWindow.setTestedStocks(self._testedStocks)
    # 主页面函数一put请求事件，就会在这里执行
    def _plotReqHandler(self, event):
        type = event.data['type']

        if type == 'bBandsStats': # 布林统计
            self._dataWindow.plotReqBBandsStats(event.data['code'],
                                             event.data['startDate'],
                                             event.data['endDate'],
                                             event.data['bBands1Period'],
                                             event.data['bBands2Period']
                                             )

        elif type == 'jaccardIndex': # 杰卡德指数
            self._dataWindow.plotReqJaccardIndex(event.data['startDate'],
                                             event.data['endDate'],
                                             event.data['param']
                                             )

        elif type == 'indexConsecutiveDayLineStats': # 指数连续日阴线统计
            self._dataWindow.plotReqIndexConsecutiveDayLineStats(event.data['startDate'],
                                             event.data['endDate'],
                                             event.data['greenLine']
                                             )

        elif type == 'limitUpStats': # 封板率统计
            self._dataWindow.plotReqLimitUpStats(event.data['startDate'],
                                             event.data['endDate']
                                             )

        elif type == 'focusAnalysis': # 热点分析
            self._dataWindow.plotReqFocusAnalysis(event.data['startDate'],
                                             event.data['endDate']
                                             )

        elif type == 'highLowDist': # 最高和最低价分布
            self._dataWindow.plotReqHighLowDist(event.data['startDate'],
                                             event.data['endDate'],
                                             size=1
                                             )

        elif type == 'test':
            self._dataViewer.plotReqTest()# 测试用

