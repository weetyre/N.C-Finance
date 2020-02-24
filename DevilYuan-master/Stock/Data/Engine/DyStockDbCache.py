import pandas as pd

from DyCommon.DyCommon import DyLogData, DyTime
from Stock.Data.DyStockDataCommon import DyStockDataCommon


class DyStockDbCache(object):
    """
        数据库Cache，为了回测时避免反复读取数据库
        Not thread safe!
        Singleton in DY system
    """

    preLoadDaysSize = 60 # how many days data forwarding preloaded for each code

    class CodeDays:
        """
            个股日线数据
        """
        def __init__(self, tradeDays, latestDateInDb):
            self.df = None
            self.tradeDays = tradeDays # [trade day], 个股交易日列表DF
            self.tradeDaysIndexes = {} # {date: index}, 个股交易日列表索引字典

            
            if not (self.tradeDays and latestDateInDb):
                return

            # Establish indexes for all range dates
            dates = DyTime.getDates(self.tradeDays[0], latestDateInDb, strFormat=True)
            j = 0 # for @self.tradeDays
            latestTradeDayIndex = 0
            for date in dates:
                if j < len(self.tradeDays) and self.tradeDays[j] == date:
                    self.tradeDaysIndexes[date] = j
                    latestTradeDayIndex = j

                    j += 1
                else:
                    self.tradeDaysIndexes[date] = latestTradeDayIndex

        def getTradeDayForAdjFactor(self, date):
            if not self.tradeDays:
                return None
            #数据库中最新的交易日
            if date > self.tradeDays[-1]:
                date = self.tradeDays[-1]
            #根据具体的交易日获得索引
            index = self.tradeDaysIndexes.get(date)
            if index is None:
                return None

            return self.tradeDays[index]#返回具体日期
        #根据输入的开始日期以及结束日期获得交易日
        def getTradeDays(self, startDate, endDate):
            if not self.tradeDays:
                return None
            #为了防止超出范围
            if startDate < self.tradeDays[0]:
                startDate = self.tradeDays[0]#向后靠拢
            startIndex = self.tradeDaysIndexes.get(startDate)

            if endDate > self.tradeDays[-1]:
                endDate = self.tradeDays[-1]#向前靠拢
            endIndex = self.tradeDaysIndexes.get(endDate)

            if startIndex is None or endIndex is None:
                return None

            # adjust start index
            if startDate > self.tradeDays[startIndex]: # @startDate is 停牌或者休市，则不向前靠拢
                startIndex += 1

            return self.tradeDays[startIndex:endIndex+1] # maybe [], means not data like None
        #根据输入的不同类型的日期类型，进行统一返回日期
        def getTradeDaysUnified(self, dates):
            if len(dates) == 2: # [start date, end date] or [base date, +/-n]
                if isinstance(dates[1], int):#[base date, +/-n]
                    startIndex = self.tradeDaysIndexes.get(dates[0])
                    if startIndex is None:
                        return None

                    n = dates[1]
                    if n >= 0:
                        endIndex = startIndex + n
                    else:
                        endIndex = startIndex

                        startIndex += n
                        startIndex = max(0, startIndex)#索引最小为零
                else:
                    return self.getTradeDays(dates[0], dates[1])

            else: # [-n, base date, +n]
                midIndex = self.tradeDaysIndexes.get(dates[1])
                if midIndex is None:
                    return None

                startIndex = midIndex + dates[0]
                startIndex = max(0, startIndex)

                endIndex = midIndex + dates[-1]

            return self.tradeDays[startIndex:endIndex+1]#因为endIndex那一位在语法上是不会获取的，所以要加1

        def getExistingDaysDates(self, startDate, endDate):
            if self.df is None:
                return []

            index = None
            if self.df.shape[0] == 1:#shape[0]获取行数，只有一行，就只有一个数据，也就只有一个日期
                if startDate == endDate and startDate in self.df.index:
                    index = self.df.index#只有一个索引也就只有一个，且这个df索引是具体日期，有可能会返回index集

            if index is None:
                index = self.df['close'][startDate:endDate].index

            return [x.strftime('%Y-%m-%d') for x in list(index)]
        #根据indicator获取df
        def getDf(self, startDate, endDate, indicators):
            if self.df is None:
                return None

            # 防止环切切不到
            df = None
            if self.df.shape[0] == 1:
                if startDate == endDate and startDate in self.df.index:
                    df = self.df

            if df is None:
                df = self.df[startDate:endDate]

            return df[indicators]
        #获取最大日期
        def getDfMaxDate(self):
            if self.df is None or self.df.empty:
                return None

            return self.df.index[-1].strftime('%Y-%m-%d')
        #添加df，然后按照索引排序
        def addDfs(self, dfs):
            if self.df is not None:
                dfs = [self.df] + dfs

            self.df = pd.concat(dfs).sort_index()
        

    def __init__(self):
        self._codeDaysDict = None
    #确保单例模式，因为处于非线程安全
    def init(self, info, dbEngine):
        if self._codeDaysDict is not None:
            return

        self._info = info
        self._dbEngine = dbEngine

        self._codeDaysDict = {} # {code: @CodeDays} 一个股票代码，映射一个codedays（内部类）实例

        # latest date of days in DB
        self._latestDateInDb = None
        date = self._dbEngine.getDaysLatestDate()
        if date is not None:
            self._latestDateInDb = date['datetime'].strftime("%Y-%m-%d")
    #初始化内部类
    def _initCodeDays(self, code, name=None):
        codeDays = self._codeDaysDict.get(code)
        if codeDays is not None:
            return codeDays

        codeInfo = code if name is None else '{}({})'.format(code, name)
        print('StockDbCache: 初始化日线数据{}...)'.format(codeInfo))

        # establish all trade days from DB
        tradyDays = self._dbEngine.codeAllTradeDays(code, name)
        if tradyDays is None:
            return None
        #在这里生成CodeDays实例
        codeDays = self.CodeDays(tradyDays, self._latestDateInDb)
        self._codeDaysDict[code] = codeDays

        return codeDays
    #rangedays是已有的标准日期，days是验证日期，返回缺失的天数
    def _getMissingDaysDates(self, rangeDays, days):
        """
            @rangDays: [date]
            @days: [date]
            get missing days dates in @rangeDays via @days
            @return: [[start date, end date]]
        """
        retDays = [] # @return
        days = set(days)
        start, end = None, None # assume we're in existing state
        for day in rangeDays:
            if start is None: # We're in existing state
                if day not in days:
                    start = day
                    end = day
            else: # We're in missing state
                if day not in days:
                    end = day # just move end of missing day
                else:
                    retDays.append([start, end])
                    start, end = None, None

        # check the last
        if start is not None:
            retDays.append([start, end])

        return retDays
    #从数据库载入到cache，具体是codedays的自己的df中
    def _load(self, code, codeDays, missingDates, name=None):
        # Do we need to preload more data?
        maxDfDate = codeDays.getDfMaxDate()
        maxMissingDate = missingDates[-1][-1]
        if maxDfDate is None or maxMissingDate > maxDfDate:
            preLoadDays = codeDays.getTradeDaysUnified([maxMissingDate, self.preLoadDaysSize])
            if preLoadDays:
                missingDates[-1][-1] = preLoadDays[-1]
        
        # load data from DB
        dfs = []
        for startDate, endDate in missingDates:
            codeInfo = code if name is None else '{}({})'.format(code, name)
            print('StockDbCache: 从数据库载入{}, {}~{}日线数据...'.format(codeInfo, startDate, endDate))

            df = self._dbEngine.getOneCodeDays(code, startDate, endDate, DyStockDataCommon.dayIndicators, name, raw=True)
            if df is not None:
                dfs.append(df)

        # save DFs
        if dfs:
            codeDays.addDfs(dfs)
    #先载入交易日，然后在缓存里找存在的交易日，然后在获取缺失的交易日，最后放入codeDays缓存(df)中，然后获取
    def _getDf(self, code, codeDays, tradeDays, indicators, name=None):
        # get missing dates
        startDate, endDate = tradeDays[0], tradeDays[-1]
        existingDays = codeDays.getExistingDaysDates(startDate, endDate)

        missingDaysDates = self._getMissingDaysDates(tradeDays, existingDays)
        if missingDaysDates: # We have missing dates, load it
            self._load(code, codeDays, missingDaysDates, name)

        return codeDays.getDf(startDate, endDate, indicators)

    #################################### Public Interfaces ####################################
    # same as DB Engine
    def getOneCodeDays(self, code, startDate, endDate, indicators, name=None):
        """
            通过绝对日期获取个股日线数据
        """
        codeDays = self._initCodeDays(code, name)
        if codeDays is None:
            return None

        tradeDays = codeDays.getTradeDays(startDate, endDate)
        if not tradeDays:
            return None

        return self._getDf(code, codeDays, tradeDays, indicators, name)
    #因为dates的格式有很多
    def getOneCodeDaysUnified(self, code, dates, indicators, name=None):
        """
            获取个股日线数据的统一接口
        """
        codeDays = self._initCodeDays(code, name)
        if codeDays is None:
            return None

        tradeDays = codeDays.getTradeDaysUnified(dates)
        if not tradeDays:
            return None

        return self._getDf(code, codeDays, tradeDays, indicators, name)

    def getAdjFactor(self, code, date, name=None):
        codeDays = self._initCodeDays(code, name)
        if codeDays is None:
            return None

        tradeDay = codeDays.getTradeDayForAdjFactor(date)
        if tradeDay is None:
            text = 'StockDbCache: @getAdjFactor({}, date={}), no adjfactor'.format(code, date)
            self._info.print(text, DyLogData.error)
            return None

        df = self._getDf(code, codeDays, [tradeDay], [DyStockDataCommon.adjFactor], name)
        return df[DyStockDataCommon.adjFactor][0]
    #基于给定日期的偏移后的日期，如果n>0 获得最后一天，如果n小于零获得第一天
    def codeTDayOffset(self, code, baseDate, n=0, strict=True):
        """
            获取基于个股偏移的交易日
        """
        codeDays = self._initCodeDays(code)
        if codeDays is None:
            return None

        tradeDays = codeDays.getTradeDaysUnified([baseDate, n])
        if not tradeDays:
            return None

        if strict:
            if len(tradeDays) != abs(n) + 1:
                text = 'StockDbCache: @codeTDayOffset({}, baseDate={}, n={}), len(tradeDays)={} is not enough to {}'.format(code, baseDate, n, len(tradeDays), abs(n) + 1)
                self._info.print(text, DyLogData.error)
                return None

        return tradeDays[0] if n < 0 else tradeDays[-1]


############################## Singleton DB Cache in DY system ##############################
dyStockDbCache = DyStockDbCache()

def DyGetStockDbCache(info, dbEngine):
    dyStockDbCache.init(info, dbEngine)
    return dyStockDbCache
