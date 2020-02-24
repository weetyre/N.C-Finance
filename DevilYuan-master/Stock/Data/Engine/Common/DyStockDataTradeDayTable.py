from datetime import *

from DyCommon.DyCommon import *

#股票数据交易日表格
class DyStockDataTradeDayTable:

    # table format
    # {year:{month:{day:[bool,index to compact table]}}}

    # compact table format
    # [date]

    def __init__(self, mongoDbEngine, gateway, info):
        self._mongoDbEngine = mongoDbEngine
        self._gateway = gateway
        self._info = info

        self._init()

    def _init(self):
        self._table = {}
        self._compactTable = []
    #
    def _buildIndex(self, date):
        year, month, day = date.split('-')

        i = 0
        while i < len(self._compactTable):
            tradeDay = self._compactTable[i]
            if date < tradeDay: break
            i += 1

        self._table[year][month][day][1] = i - 1#相对于压缩表的索引值的建立
    #更新指数
    def _updateIndex(self):
        self._compactTable.sort()

        preDate = None
        oldest = None
        date = None # will be latest after loop

        years = sorted(self._table)#升序年排序
        for year in years:
            months = sorted(self._table[year])#升序月份排序
            for month in months:
                days = sorted(self._table[year][month])#升序天数排序
                for day in days:
                    date = year + '-' + month + '-' + day

                    if not oldest: oldest = date#第一天，最早的那一天

                    # index should be built based on continous days
                    if preDate:
                        if DyTime.getDateStr(preDate, 1) != date:
                            self._info.print("Days in TradeDay Table aren't continous!", DyLogData.error)
                            return False
                    preDate = date # 付给前一天看看是不是属于递进的一天

                    # build index for day
                    self._buildIndex(date)

        return True
    #转换交易日的格式，并且递增排列
    def _convertTradeDays(self, tradeDays):
        tradeDays = [doc['datetime'].strftime("%Y-%m-%d") for doc in tradeDays]

        tradeDays.sort()

        return tradeDays
    #有偏移的日期,只返回数据表为T
    def _load3(self, startDate, endDate, n):
        # 分部分载入
        # front part
        startDateNew, endDateNew = startDate, endDate
        if isinstance(startDate, int):
            startDateNew, endDateNew = endDateNew, startDateNew

        frontStartDate, frontEndDate, frontTradeDays = self._load2(startDateNew, endDateNew)
        if frontStartDate is None: return None, None, None

        # back part
        backStartDate, backEndDate, backTradeDays = self._load2(endDate, n)
        if backStartDate is None: return None, None, None

        # combine trade days, always zero offset trade day is duplicated
        for day in frontTradeDays:
            if day in backTradeDays:
                backTradeDays.remove(day)

        tradeDays = frontTradeDays + backTradeDays
        tradeDays.sort()

        # combine date range
        if frontStartDate < backStartDate:
            startDate = frontStartDate
        else:
            startDate = backStartDate

        if backEndDate > frontEndDate:
            endDate = backEndDate
        else:
            endDate = frontEndDate

        # combine with trade days
        startDateNew = tradeDays[0]
        endDateNew = tradeDays[-1]

        if startDate < startDateNew:
            startDateNew = startDate

        if endDate > endDateNew:
            endDateNew = endDate

        return  startDateNew, endDateNew, tradeDays
    #只返回交易日数据表中为True的数据
    def _load2(self, startDate, endDate):
        if isinstance(endDate, int):#有偏移的情况，因为会有n的正负得情况
            tradeDays = self._mongoDbEngine.getTradeDaysByRelative(startDate, endDate) # 交易日（只返回数据表为T）
            if tradeDays is None: return None, None, None

            assert(tradeDays)

            tradeDays = self._convertTradeDays(tradeDays)

            startDateNew = tradeDays[0]
            endDateNew = tradeDays[-1]
            #因为偏移有正负
            if startDate > endDateNew:
                endDateNew = startDate

            elif startDate < startDateNew:
                startDateNew = startDate

            return  startDateNew, endDateNew, tradeDays #这个new是基于新的交易日Date(从此返回的为偏移后的)

        else:#通过绝对日期获取
            tradeDays = self._mongoDbEngine.getTradeDaysByAbsolute(startDate, endDate)
            if tradeDays is None: return None, None, None

            tradeDays = self._convertTradeDays(tradeDays)

            return  startDate, endDate, tradeDays
    #载入交易日数据（输入参数起始日期-截止日期）
    def load(self, dates):
        self._info.print("开始载入交易日数据{0}...".format(dates))

        # 初始化
        self._init()

        # 根据不同格式载入
        if len(dates) == 2:
            startDate, endDate, tradeDays = self._load2(dates[0], dates[1])
        else:
            startDate, endDate, tradeDays = self._load3(dates[0], dates[1], dates[2])

        if startDate is None:
            return False

        if not self._set2Table(startDate, endDate, tradeDays):
            return False

        self._info.print("交易日数据[{0}, {1}]载入完成".format(startDate, endDate))

        return True
    #获得最后一天
    def tLatestDay(self):
        return self._compactTable[-1] if self._compactTable else None
    #获得第一天
    def tOldestDay(self):
        return self._compactTable[0] if self._compactTable else None
    #根据偏移在压缩格式的表里获取日期
    def tDaysOffset(self, base, n):
        if isinstance(base, datetime):
            base = base.strftime("%Y-%m-%d")

        base = base.split('-')

        try:
            index = self._table[base[0]][base[1]][base[2]][1]
        except Exception as ex:
            pass
        else:
            # find it
            nIndex = index + n
            if nIndex >= 0 and nIndex < len(self._compactTable):#在正常的范围内
                return self._compactTable[nIndex]

        return None
    #判断给你一个日期区间，他是否在table里面
    def isIn(self, start, end):
        dates = DyTime.getDates(start, end)

        for date in dates:
            date = date.strftime("%Y-%m-%d").split('-')
            if date[0] not in self._table:
                return False
            if date[1] not in self._table[date[0]]:
                return False
            if date[2] not in self._table[date[0]][date[1]]:
                return False

        return True
    #
    def get(self, start, end):
        """ @return: [trade day] """

        dates = DyTime.getDates(start, end)

        tradeDays = []
        for date in dates:
            dateSave = date.strftime("%Y-%m-%d")
            date = dateSave.split('-')
            if date[0] in self._table:
                if date[1] in self._table[date[0]]:
                    if date[2] in self._table[date[0]][date[1]]:
                        if self._table[date[0]][date[1]][date[2]][0]: #bool 来判断是否是交易日
                            tradeDays.append(dateSave)

        return tradeDays
    #
    def _update2Db(self, startDate, endDate, tradeDays):

        # convert to MongoDB format
        datesForDb = []
        dates = DyTime.getDates(startDate, endDate)

        for date in dates:
            doc = {'datetime':date}

            if date.strftime('%Y-%m-%d') in tradeDays:
                doc['tradeDay'] = True
            else:
                doc['tradeDay'] = False

            datesForDb.append(doc)

        # update into DB 包括 T,F 是否是交易日
        return self._mongoDbEngine.updateTradeDays(datesForDb)
    #
    def _set(self, startDate, endDate, tradeDays):
        return self._set2Table(startDate, endDate, tradeDays) and self._update2Db(startDate, endDate, tradeDays)
    #设置到Table表里面
    def _set2Table(self, start, end, tradeDays):
        """ [@start, @end] is range """

        dates = DyTime.getDates(start, end)

        dates = [x.strftime("%Y-%m-%d")  for x in dates]
        days = tradeDays #

        for day in dates:
            dayTemp = day.split('-')

            if dayTemp[0] not in self._table:
                self._table[dayTemp[0]] = {}

            if dayTemp[1] not in self._table[dayTemp[0]]:
                self._table[dayTemp[0]][dayTemp[1]] = {}

            if day in days:
                self._table[dayTemp[0]][dayTemp[1]][dayTemp[2]] = [True, -1]
            else:
                self._table[dayTemp[0]][dayTemp[1]][dayTemp[2]] = [False, -1]

        self._compactTable.extend(days) #里面放的是实打实的交易日，所以是压缩表，而Table里面什么都会有（全部日期）

        return self._updateIndex()#table相对于压缩表的索引更新
    #
    def update(self, startDate, endDate):
        self._info.print('开始更新交易日数据...')

        if self.load([startDate, endDate]):
            self._info.print('交易日数据已在数据库')
            return True

        tradeDays = self._gateway.getTradeDays(startDate, endDate)
        if tradeDays is None: return False

        # set to tables and then update to DB
        if not self._set(startDate, endDate, tradeDays):
            return False

        self._info.print('交易日数据更新完成')
        return True
    #
    def getLatestDateInDb(self):
        date = self._mongoDbEngine.getDaysLatestDate()
        if date is None: return None

        return date['datetime'].strftime("%Y-%m-%d")
    #
    def getLatestTradeDayInDb(self):
        date = self._mongoDbEngine.getDaysLatestTradeDay()
        if date is None: return None

        return date['datetime'].strftime("%Y-%m-%d")
    #从数据库（加t日偏移）
    def tDaysOffsetInDb(self, base, n=0):
        startDate, endDate, tradeDays = self._load2(base, n)
        if startDate is None: return None

        if n <= 0:
            n -= 1

        try:
            day = tradeDays[n]
        except Exception as ex:
            day = None

        return day
    #
    def tDaysCountInDb(self, startDate=None, endDate=None):
        """
            从数据库获取指定日期范围的交易日数
        """
        tradeDays = self._mongoDbEngine.getTradeDaysByAbsolute(startDate, endDate)
        if tradeDays is None:
            return None

        return len(tradeDays)
