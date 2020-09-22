
#根据不同的数据类型，给引擎分配不同的线程
class DyStockDataEventHandType:
    DY_STOCK_DATA_HIST_TICKS_HAND_NBR = 5 # TDX support max 5 live connections 线程数为5
    
    stockHistTicksHandNbr = DY_STOCK_DATA_HIST_TICKS_HAND_NBR
    ticksEngine = DY_STOCK_DATA_HIST_TICKS_HAND_NBR#tick
    daysEngine = DY_STOCK_DATA_HIST_TICKS_HAND_NBR + 1#日数据
    strategyDataPrepare = DY_STOCK_DATA_HIST_TICKS_HAND_NBR + 2#策略数据准备
    other = DY_STOCK_DATA_HIST_TICKS_HAND_NBR + 3#其他

    nbr = DY_STOCK_DATA_HIST_TICKS_HAND_NBR + 4#最大引擎线程数，每多一个功能，加一个线程

#数据请求类（股票代码，以及日期）
class DyStockHistTicksReqData:
    def __init__(self, code, date):
        self.code = code
        self.date = date
#数据确认类（股票代码，以及日期，加请求的数据）
class DyStockHistTicksAckData:
    noData = 'noData'

    def __init__(self, code, date, data):
        self.code = code
        self.date = date
        self.data = data

"""
                ["股本指标",
                    ["流通A股", 'float_a_shares'],
                    ["A股合计", 'share_totala']
                ],
                
                ["行情指标",
                    ["开盘价", 'open'],
                    ["收盘价", 'close'],
                    ["最高价", 'high'],
                    ["最低价", 'low'],
                    ["成交量", 'volume'],
                    ["成交额", 'amt'],
                    ["换手率", 'turn'],
                    ["净流入资金", 'mf_amt'],
                    ["净流入量", 'mf_vol']
                ],
                以下类确定了获取数据的指标，以及规定了默认的数据源
"""
class DyStockDataCommon:# 默认的日线指标
    # Wind的volume是成交量，单位是股数。数据库里的成交量也是股数。
    dayIndicators = ['open', 'high', 'low', 'close', 'volume', 'amt', 'turn', 'adjfactor']
    adjFactor = 'adjfactor'#股票复权因子

    logDetailsEnabled = False

    defaultHistTicksDataSource = '智能' # '新浪', '腾讯' , '网易', '智能'
