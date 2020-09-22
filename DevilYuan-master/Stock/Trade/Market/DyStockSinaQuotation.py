import asyncio
import aiohttp
import re
import urllib.request

from DyCommon.DyCommon import *
from EventEngine.DyEvent import *
from ..DyStockTradeCommon import *

# 股票新浪引用
class DyStockSinaQuotation(object):
    """ 被动类，也就是说本身不会注册事件。有个例外，注册了UI的proxy的配置事件。
        这个事件本身没有数据互斥的影响。
    """

    maxNum = 800
    grep_detail = re.compile(r'(\w+)=([^\s][^,]+?)%s%s' % (r',([\.\d]+)' * 29, r',([-\.\d:]+)' * 2)) # 字符串查找
    stock_api = 'http://hq.sinajs.cn/?format=text&list='# 新浪股票接口
    # 四大指数
    cybSinaIndex = 'sz399006'
    cybzSinaIndex = 'sz399102'
    zxbSinaIndex = 'sz399005'
    zxbzSinaIndex = 'sz399101'


    def __init__(self, eventEngine, info):
        self._info = info
        
        self._enableProxy = False
        self._registerEvent(eventEngine)

        self._stockList = [] # include indexes
        self._sessions = []
    # 初始化
    def init(self):
        for s in self._sessions:# 先关闭所有的session
            s.close()

        self._stockList = [] # include indexes
        self._sessions = []
    # 激活代理
    def _enableProxyHandler(self, event):
        # Note: Should start proxy firstly, it's much tricky that this flag is updated by other hand, not stockSianQuotation hand.
        # The situation is that if without proxy, it will take some time for http visiting failed.
        # During that time, 1s timer event will be cumulated at stockSianQuotation hand queue so that Ui event cannot be handled on time.
        if event.data:
            proxy_support = urllib.request.ProxyHandler({'http': 'x.x.x.x:8000'})
            opener = urllib.request.build_opener(proxy_support)
            urllib.request.install_opener(opener)

        # set flag
        self._enableProxy = event.data
    # 注册代理事件
    def _registerEvent(self, eventEngine):
        # Note: not stockSianQuotation hand
        eventEngine.register(DyEventType.enableProxy, self._enableProxyHandler)
    # add之后，加入list
    def _add2List(self, stockCodes):
        # stored list
        allStocks = []

        for stock in self._stockList:# 刚开始是空
            allStocks += stock.split(',')

        # combine with new stocks
        allStocks += stockCodes# list

        # generate new stock list
        self._stockList = []
        for i in range(0, len(allStocks), self.maxNum):# 后面的是步长，也就是800支
            self._stockList.append(','.join(allStocks[i:i + self.maxNum]))# [‘...,...,...’(最多800个)，‘...,...,...’]，然后放到list

    def addIndexes(self, indexes):
        indexes = list(
                map(lambda index: ('sh%s' if index.startswith(('0')) else 'sz%s') % index[:-3],
                    indexes))

        self._add2List(indexes)
    # 添加
    def add(self, stockCodes):
        sinaStocks = list(
                map(lambda stockCode: ('sh%s' if stockCode.startswith(('5', '6', '9')) else 'sz%s') % stockCode[:-3],
                    stockCodes))# 做了一下新浪数据格式转换

        self._add2List(sinaStocks)
    # 获取数据
    def get(self):
        return self._get_stock_data(self._stockList)# 字典返回结果数据，通过协程的方式获取
    # 协程装饰器 这是启用代理的情况下运行的函数
    @asyncio.coroutine
    def _get_stocks_by_range_with_proxy(self, i, params):
        response_text = urllib.request.urlopen(self.stock_api + params).read().decode('GBK')

        return response_text

    @asyncio.coroutine
    def _get_stocks_by_range(self, i, params):
        # create HTTP sessions when @self._stockList changed
        if len(self._sessions) != len(self._stockList):
            for s in self._sessions:
                yield from s.close()

            self._sessions = [aiohttp.ClientSession() for _ in range(len(self._stockList))]

        session = self._sessions[i]

        r = yield from session.get(self.stock_api + params, timeout=1)
        response_text = yield from r.text()

        return response_text
    # 获取股票数据
    def _get_stock_data(self, stock_list):
        if not stock_list:
            return {}

        # async run
        try:
            loop = asyncio.get_event_loop()# python 协程，实现并发，获取时间循环
        except RuntimeError:
            loop = asyncio.new_event_loop()# 错误新建 时间循环
            asyncio.set_event_loop(loop)# 并且设置

        # coroutines # 确认获取函数
        get_stocks_by_range_func =  self._get_stocks_by_range_with_proxy if self._enableProxy else self._get_stocks_by_range
        coroutines = []
        for i, params in enumerate(stock_list):
            coroutine = get_stocks_by_range_func(i, params)
            coroutines.append(coroutine)

        try:
            res = loop.run_until_complete(asyncio.gather(*coroutines))# 运行直到结束
        except Exception as ex:
            self._info.print("获取新浪股票实时行情异常: {0}".format(repr(ex)), DyLogData.warning)
            return {}

        return self._format_response_data(res)# 格式返回数据，字典返回
    # 格式返回数据
    def _format_response_data(self, rep_data):
        stocks_detail = ''.join(rep_data)# 变成了字符串
        result = self.grep_detail.finditer(stocks_detail)
        stock_dict = dict()
        for stock_match_object in result:
            stock = stock_match_object.groups()# 转成Set,逗号分隔
            stock_dict[stock[0]] = dict(
                    name=stock[1],
                    open=float(stock[2]),
                    pre_close=float(stock[3]), # 昨日收盘价(前复权）
                    now=float(stock[4]),
                    high=float(stock[5]),
                    low=float(stock[6]),
                    buy=float(stock[7]), # 竞买价，即“买一”报价
                    sell=float(stock[8]), # 竞卖价，即“卖一”报价
                    volume=int(stock[9]), # 今日累计成交的股票数，由于股票交易以一百股为基本单位，所以在使用时，通常把该值除以一百
                    amount=float(stock[10]), # 今日累计成交金额，单位为“元”，为了一目了然，通常以“万元”为成交金额的单位，所以通常把该值除以一万
                    bid1_volume=int(stock[11]), # “买一”申请股数
                    bid1=float(stock[12]), # “买一”报价
                    bid2_volume=int(stock[13]),
                    bid2=float(stock[14]),
                    bid3_volume=int(stock[15]),
                    bid3=float(stock[16]),
                    bid4_volume=int(stock[17]),
                    bid4=float(stock[18]),
                    bid5_volume=int(stock[19]),
                    bid5=float(stock[20]),
                    ask1_volume=int(stock[21]), # “卖一”申报股数
                    ask1=float(stock[22]), # “卖一”报价
                    ask2_volume=int(stock[23]),
                    ask2=float(stock[24]),
                    ask3_volume=int(stock[25]),
                    ask3=float(stock[26]),
                    ask4_volume=int(stock[27]),
                    ask4=float(stock[28]),
                    ask5_volume=int(stock[29]),
                    ask5=float(stock[30]),
                    date=stock[31],
                    time=stock[32],
            )

        # 调整创小板的成交量和成交额
        # 创业板
        cyb = stock_dict.get(self.cybSinaIndex)# 创业板指
        cybz = stock_dict.get(self.cybzSinaIndex)# 创业板宗
        if cyb and cybz:
            cyb['volume'] = cybz['volume']
            cyb['amount'] = cybz['amount']

        # 中小板
        zxb = stock_dict.get(self.zxbSinaIndex)# 中小板指
        zxbz = stock_dict.get(self.zxbzSinaIndex)# 中小板综
        if zxb and zxbz:
            zxb['volume'] = zxbz['volume']
            zxb['amount'] = zxbz['amount']

        return stock_dict
