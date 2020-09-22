import os
from time import sleep
import copy
import subprocess
import json

from DyCommon.DyCommon import *
from ..DyStockTradeCommon import *

# 券商交易接口
class DyTrader(object):
    """
        券商交易接口基类
    """
    name = None# 什么交易接口,列如：Web，子类覆盖，只有web

    heartBeatTimer = 60
    pollingCurEntrustTimer = 1
    maxRetryNbr = 3 # 最大重试次数

    curEntrustHeaderNoIndex = None
    curEntrustHeaderStateIndex = None


    def __init__(self, eventEngine, info, configFile=None, accountConfigFile=None):
        self._eventEngine = eventEngine
        self._info = info

        # 载入券商的配置文件
        self.__readConfig(configFile, accountConfigFile)
        self._tradePrefix = None if self._config is None else self._config.get('prefix')
    # 文件转json
    def _file2dict(self, file):
        with open(file) as f:
            return json.load(f)
    #
    def _curInit(self):
        self._curDay = datetime.now().strftime("%Y-%m-%d")# 系统当前日子

        # 当日委托，用于比较是否有委托状态更新
        self._curEntrusts = None

        # 保存的资金和持仓数据
        # 避免实时从券商接口获取
        self._balance = None
        self._positions = None

        self._exchangeDatetime = None # 最新交易所的时间，来自于监控到的指数更新的最新datetime. Currently, not used!!!

        self._isRegisterStockMarketTicks = False
    # 登陆前处理
    def _preLogin(self):
        pass
    # 退出后处理
    def _postLogout(self):
        pass
    # 首先执行登录
    def login(self):
        """ 登录 """
        self._info.print('开始登陆[{}]{}交易接口...'.format(self.brokerName, self.name), DyLogData.ind)
        
        # 初始化
        self._curInit()

        self._preLogin()

        # login
        while True:
            try:
                if self._login():# 调用的SimuTrader的login（完成添加股票到监控，以及到新浪，以及本地文件更新）
                    break# 重复尝试登陆，登录成功退出循环
            except Exception as ex:
                self._info.print('[{}]{}交易接口登陆异常: {}'.format(self.brokerName, self.name, str(ex)), DyLogData.warning)

        self._registerEvent()

        self._info.print('[{}]{}交易接口登陆成功'.format(self.brokerName, self.name), DyLogData.ind)
    # 退出登录
    def logout(self, oneKeyHangUp=False):
        """ 退出登录 """

        # 注销事件
        self._unregisterEvent()

        self._info.print('开始退出[{}]{}交易接口...'.format(self.brokerName, self.name), DyLogData.ind)

        logoutSucess = self._logout(oneKeyHangUp)# 具体的交易券商接口，模拟直接保存本地盘

        if logoutSucess:
            self._info.print('[{}]{}交易接口退出成功'.format(self.brokerName, self.name), DyLogData.ind)
        else:
            self._info.print('[{}]{}交易接口退出失败'.format(self.brokerName, self.name), DyLogData.error)

        self._postLogout()
    # 保持 token 的有效性
    def _sendHeartBeat(self, event):
        """
            每隔@self.heartBeatTimer秒查询指定接口保持 token 的有效性
        """
        x, y = self.getBalance(parse=False)
        if x is None:
            self._info.print('{}: 心跳失败'.format(self.brokerName), DyLogData.warning)
    # 读取config
    def __readConfig(self, configFile, accountConfigFile):
        """ 读取 config """
        self._config = None if configFile is None else self._file2dict(configFile)
        self._accountConfig = None if accountConfigFile is None else self._file2dict(accountConfigFile)

    def _recognizeVerifyCode(self, imagePath, broker):
        """
            识别验证码，返回识别后的字符串，使用 tesseract 实现
            @imagePath: 图片路径
            @broker: 券商
            @return: recognized verify code string
        """
        # 优先JAVA程序识别
        if broker in ['ht', 'yjb', 'gtja']:
            verifyCodeTool = 'getcode_jdk1.5.jar' if broker in ['ht', 'gtja'] else 'yjb_verify_code.jar guojin'
            # 检查 java 环境，若有则调用 jar 包处理
            output = subprocess.getoutput('java -version')

            if 'java version' not in output:
                self._info.print("No JRE installed!", DyLogData.warning)
            else:
                output = subprocess.getoutput(
                        'java -jar %s %s' % (
                            os.path.join(os.path.dirname(__file__), 'ThirdLibrary', verifyCodeTool), imagePath))

                ncodeStart = output.find('code=')
                if ncodeStart == -1: return ""

                return output[ncodeStart + len('code='):]

        # 调用 tesseract 识别
        # ubuntu 15.10 无法识别的手动 export TESSDATA_PREFIX
        systemResult = os.system('tesseract {} result -psm 7'.format(imagePath))
        if systemResult != 0:
            os.system(
                    'export TESSDATA_PREFIX="/usr/share/tesseract-ocr/tessdata/"; tesseract {} result -psm 7'.format(
                            imagePath))

        # 获取识别的验证码
        verifyCodeResult = 'result.txt'
        try:
            with open(verifyCodeResult) as f:
                recognizedCode = f.readline()
        except UnicodeDecodeError:
            try:
                with open(verifyCodeResult, encoding='gbk') as f:
                    recognizedCode = f.readline()
            except:
                recognizedCode = ''

        # 移除空格和换行符
        returnIndex = -1
        recognizedCode = recognizedCode.replace(' ', '')[:returnIndex]

        os.remove(verifyCodeResult)

        return recognizedCode
    # 检查新的委托
    def _checkNewEntrusts(self, newEntrusts):
        """
            Prevent we get wrong data from broker
        """
        # We think no need to check entrusts format, which will be handled by subclass.
        if self.curEntrustHeaderNoIndex is None:# 模拟的是空，就是委托header号索引
            return True

        maxIndex = max(self.curEntrustHeaderNoIndex, self.curEntrustHeaderStateIndex)# header 状态索引

        for newEntrust in newEntrusts:
            if maxIndex >= len(newEntrust):
                self._info.print('{}: 当日委托数据错误: {}'.format(self.brokerName, newEntrust), DyLogData.warning)
                return False
        
        return True
    # 轮询函数，是一个计时器函数，1秒运行一次
    def _pollCurEntrusts(self, event):
        """
            定时轮询当日委托直到所有委托都是完成状态
        """
        # 从券商GET当日委托
        header, newEntrusts = self.getCurEntrusts()# 调用的是券商的接口
        if header is None:
            return

        if not self._checkNewEntrusts(newEntrusts):
            return
        
        # compare state for each entrust
        stateChange, allDone = self._compareEntrusts(self._curEntrusts, newEntrusts)

        # new current entrusts
        self._curEntrusts = newEntrusts# 直接赋值就行，因为都是一块给

        # 委托状态有更新
        if stateChange:
            self.updateAccount((header, self._curEntrusts))# 更新整个账户状态，券商类持仓，以及账户策略持仓

        # 所有委托都完成了, no need polling any more
        if allDone:
            self._eventEngine.unregisterTimer(self._pollCurEntrusts, DyStockTradeEventHandType.brokerEngine, self.pollingCurEntrustTimer)# 接注册
    # 注册
    def _registerEvent(self):
        """
            login成功后注册委托事件和心跳事件
        """
        # heart beat timer
        if self.heartBeatTimer > 0:
            self._eventEngine.registerTimer(self._sendHeartBeat, DyStockTradeEventHandType.brokerEngine, self.heartBeatTimer)
        # 买入，卖出，取消
        self._eventEngine.register(DyEventType.stockBuy + self.broker, self._stockBuyHandler, DyStockTradeEventHandType.brokerEngine)# 券商引擎2
        self._eventEngine.register(DyEventType.stockSell + self.broker, self._stockSellHandler, DyStockTradeEventHandType.brokerEngine)
        self._eventEngine.register(DyEventType.stockCancel + self.broker, self._stockCancelHandler, DyStockTradeEventHandType.brokerEngine)

        self._eventEngine.register(DyEventType.stockBrokerRetry + self.broker, self._stockBrokerRetryHandler, DyStockTradeEventHandType.brokerEngine)
    # 解除注册
    def _unregisterEvent(self):
        # heart beat timer
        self._eventEngine.unregisterTimer(self._sendHeartBeat, DyStockTradeEventHandType.brokerEngine, self.heartBeatTimer)

        self._eventEngine.unregister(DyEventType.stockBuy + self.broker, self._stockBuyHandler, DyStockTradeEventHandType.brokerEngine)
        self._eventEngine.unregister(DyEventType.stockSell + self.broker, self._stockSellHandler, DyStockTradeEventHandType.brokerEngine)

        # 有可能委托轮询timer启动了，注销它
        self._eventEngine.unregisterTimer(self._pollCurEntrusts, DyStockTradeEventHandType.brokerEngine, self.pollingCurEntrustTimer)# 每一秒轮询一次

        self._eventEngine.unregister(DyEventType.stockBrokerRetry + self.broker, self._stockBrokerRetryHandler, DyStockTradeEventHandType.brokerEngine)

        self._eventEngine.unregister(DyEventType.stockMarketTicks, self._stockMarketTicksHandler, DyStockTradeEventHandType.brokerEngine)
    # 更新(真正券商的买结果)
    def _updateEntrustWithBrokerEntrustId(self, entrust, brokerEntrustId):
        entrust = copy.copy(entrust)
        entrust.brokerEntrustId = brokerEntrustId

        event = DyEvent(DyEventType.stockEntrustUpdate + self.broker)
        event.data = entrust

        self._eventEngine.put(event)
    # 每次手动策略买的时候，就会生成委托后，会执行这个函数
    def _stockBuyHandler(self, event):
        entrust = event.data
        # 模拟账户只会返回TorF
        ret = self.buy(entrust.code, entrust.name, entrust.price, entrust.totalVolume)
        if ret: # success
            if ret is not True: # success with broker entrust ID
                self._updateEntrustWithBrokerEntrustId(entrust, ret)

            self._postfixEntrustAction()
        else:
            self._discardEntrust(entrust)

            self.updateCapitalPositions()
    # 卖
    def _stockSellHandler(self, event):
        entrust = event.data

        ret = self.sell(entrust.code, entrust.name, entrust.price, entrust.totalVolume)
        if ret: # success
            if ret is not True: # success with broker entrust ID
                self._updateEntrustWithBrokerEntrustId(entrust, ret)

            self._postfixEntrustAction()
        else:# 失败
            self._discardEntrust(entrust)# 像账户管理发送委托状态

            self.updateCapitalPositions()# 更新资金，更新持仓
    # 取消
    def _stockCancelHandler(self, event):
        entrust = event.data

        self.cancel(entrust)# 对于模拟券商，直接返回错误，因为以已经deal，无法撤销
    # 买，卖之后要处理
    def _postfixEntrustAction(self):
        """
            响应委托事件的后续操作
        """
        # 从券商GET资金状况, 主要是为了及时更新账户的资金信息
        self.updateCapital()

        # 启动当日委托状态轮询
        self._eventEngine.registerTimer(self._pollCurEntrusts, DyStockTradeEventHandType.brokerEngine, self.pollingCurEntrustTimer)# 然后注册轮询，监控委托
    # 更新整个账户状态
    def updateAccount(self, curEntrusts=None):
        """
            从券商更新整个账户状况: 当日委托，当日成交，资金，持仓。
            由于账户管理类是根据委托状态匹配成交，所以委托一定要早于成交更新。
            !!!updating sequence is very tricky.
            @curEntrusts: (header, rows), which is got from broker
        """
        # 当日委托
        self.updateCurEntrusts(curEntrusts)

        # 当日成交
        self.updateCurDeals()

        # 资金状况和持仓
        self.updateCapitalPositions()
    # 更新当日成交
    def updateCurDeals(self):
        # 当日成交
        header, rows= self.getCurDeals()
        if header is None:
            self._putBrokerRetryEvent(self.updateCurDeals)
            return

        event = DyEvent(DyEventType.stockCurDealsUpdate + self.broker)
        event.data['header'] = header
        event.data['rows'] = rows

        self._eventEngine.put(event)
    # 先更新当日委托
    def updateCurEntrusts(self, curEntrusts=None):
        """
            @curEntrusts: (header, rows), which is got from broker
        """
        # 当日委托
        if curEntrusts is None:
            header, curEntrusts= self.getCurEntrusts()
        else:
            header, curEntrusts = curEntrusts

        if header is None:
            self._putBrokerRetryEvent(self.updateCurEntrusts)
            return

        event = DyEvent(DyEventType.stockCurEntrustsUpdate + self.broker)
        event.data['header'] = header
        event.data['rows'] = curEntrusts

        self._eventEngine.put(event)
    # 接着运行这个同步持仓方法，自己除复权过后还需要在同步一次（或者说收到最新tick后）
    def syncPos(self):
        """
            券商接口首次登陆时，必须要调用此接口完成券商接口账户和账户管理类的持仓同步，
            以获取持仓复权因子和成本价。
        """
        # 持仓
        header = None
        while header is None: # 直到成功
            header, rows, autoForegroundHeaderName = self.getPositions(fromBroker=True)

        event = DyEvent(DyEventType.stockPosSyncFromBroker + self.broker) # 券商接口持仓同步事件
        event.data['header'] = header
        event.data['rows'] = rows
        event.data['autoForegroundHeaderName'] = autoForegroundHeaderName

        self._eventEngine.put(event)

        self._registerStockMarketTicksEvent(rows)
    # 注册监控市场行情事件，同步后持仓调用
    def _registerStockMarketTicksEvent(self, positions):
        """
            只监控市场行情事件，但不推送给市场引擎要获取的股票代码。这个由对应的账管理类来完成。
            这样只是时间有点延迟。
            @positions: [[x, x, x, ...]] or [] means no position
        """
        # 如果有持仓，则注册@stockMarketTicks事件
        if positions:
            if not self._isRegisterStockMarketTicks:# 默认是False
                self._eventEngine.register(DyEventType.stockMarketTicks, self._stockMarketTicksHandler, DyStockTradeEventHandType.brokerEngine) # 股票池行情的Tick事件
                self._isRegisterStockMarketTicks = True
        else:
            if self._isRegisterStockMarketTicks:
                self._eventEngine.unregister(DyEventType.stockMarketTicks, self._stockMarketTicksHandler, DyStockTradeEventHandType.brokerEngine)
                self._isRegisterStockMarketTicks = False

    def updatePositions(self, fromBroker=True):
        """
            @fromBroker: True - 从券商接口获取持仓数据，False - 从本地获取，本地持仓会根据行情推送的数据进行更新，比从券商获取效率高。
        """
        # 持仓
        header, rows, autoForegroundHeaderName = self.getPositions(fromBroker=fromBroker)
        if header is None:
            self._putBrokerRetryEvent(self.updatePositions)
            return
        # 更新账户持仓，策略持仓，监控股票，以及持仓UI，卖对话框UI
        event = DyEvent(DyEventType.stockPositionUpdate + self.broker)
        event.data['header'] = header
        event.data['rows'] = rows
        event.data['autoForegroundHeaderName'] = autoForegroundHeaderName

        self._eventEngine.put(event)

        self._registerStockMarketTicksEvent(rows)
    # 资金状况和持仓更新
    def updateCapitalPositions(self, fromBroker=True):
        # 资金状况
        self.updateCapital(fromBroker)

        # 持仓
        self.updatePositions(fromBroker)
    # 更新资金状况
    def updateCapital(self, fromBroker=True):
        header, rows = self.getBalance(fromBroker=fromBroker)
        if header is None:
            self._putBrokerRetryEvent(self.updateCapital)
            return

        event = DyEvent(DyEventType.stockCapitalUpdate + self.broker)# 然后会更新对应的账户
        event.data['header'] = header
        event.data['rows'] = rows

        self._eventEngine.put(event)
    # 发送一个重试函数
    def _putBrokerRetryEvent(self, func):
        event = DyEvent(DyEventType.stockBrokerRetry + self.broker)
        event.data['func'] = func

        self._eventEngine.put(event)
    # 变为废单
    def _discardEntrust(self, entrust):
        entrust = copy.copy(entrust)
        entrust.status = DyStockEntrust.Status.discarded# 已废

        event = DyEvent(DyEventType.stockEntrustUpdate + self.broker)# 告诉账户管理，更新
        event.data = entrust

        self._eventEngine.put(event)
    # 券商接口重试事件，在这执行
    def _stockBrokerRetryHandler(self, event):
        func = event.data['func']

        self._info.print('{}: 重试{}...'.format(self.brokerName, func.__name__), DyLogData.warning)
        sleep(1)# 因为有可能网络原因处理函数失败，所以要重试
        func()
    # 是否是有效的Ticks
    def __isValidTicks(self, ticks):
        """
            是否是有效的Ticks
            @return: bool
        """
        if not DyStockTradeCommon.enableCtaEngineTickOptimization:# 打开实盘CTA引擎的Tick数据的优化，主要是调试实盘策略，打开即调试
            return True

        szIndexTick = ticks.get(DyStockCommon.szIndex)# 必须有 深证成指 '399001.SZ'
        if szIndexTick is None:
            return False

        if szIndexTick.date != self._curDay:
            return False

        # 确保现在是有效交易时间
        if not '09:25:00' <= szIndexTick.time < '15:00:10':
            return False

        return True

    def __setExchangeDatetime(self, ticks):
        szIndexTick = ticks.get(DyStockCommon.szIndex)
        shIndexTick = ticks.get(DyStockCommon.shIndex)

        if szIndexTick is not None and shIndexTick is not None:
            self._exchangeDatetime = max(szIndexTick.datetime, shIndexTick.datetime)
        elif szIndexTick is not None:
            self._exchangeDatetime = szIndexTick.datetime
        elif shIndexTick is not None:
            self._exchangeDatetime = shIndexTick.datetime
    # 市场行情处理
    def _stockMarketTicksHandler(self, event):
        """
            市场行情处理
        """
        # unpack
        ticks = event.data

        # 设置交易所的最新时间
        #self.__setExchangeDatetime(ticks)

        # call virtual @onTicks of instance
        if not self.__isValidTicks(ticks):
            return

        self.onTicks(ticks)## 就是持仓他有很多子数据[0],[1],[2],[3]，需要这两个函数一起更新才能完 以及balence, 更新完会推送相关组件

        # update from local tickly for UI
        # capital
        header, rows = self.getBalance(fromBroker=False)
        if header is not None:
            event = DyEvent(DyEventType.stockCapitalTickUpdate + self.broker)
            event.data['header'] = header
            event.data['rows'] = rows

            self._eventEngine.put(event)

        # positions
        header, rows, autoForegroundHeaderName = self.getPositions(fromBroker=False)
        if header is not None:
            event = DyEvent(DyEventType.stockPositionTickUpdate + self.broker)
            event.data['header'] = header
            event.data['rows'] = rows
            event.data['autoForegroundHeaderName'] = autoForegroundHeaderName

            self._eventEngine.put(event)

    def onTicks(self, ticks):
        """
            由子类重载来更新实时持仓和账户信息
        """
        pass
    # 券商接口的重试装饰器
    def retryWrapper(func):
        """
            券商接口的重试装饰器
            装饰跟券商网络相关的接口
        """
        def wrapper(self, *args, **kwargs):
            for _ in range(self.maxRetryNbr):# 最大重试次数3
                x = func(self, *args, **kwargs)# getBalance 等相关函数

                if isinstance(x, tuple):
                    if x[0] is not None:
                        return x
                else:
                    if x is not None and x is not False:
                        return x

            self._info.print('{}: {}失败{}次'.format(self.brokerName, func.__name__, self.maxRetryNbr), DyLogData.error)
            return x

        return wrapper
    # 获得委托的状态
    def _getEntrustState(self, entrustNo, entrusts):
        for entrust in entrusts:
            if entrust[self.curEntrustHeaderNoIndex] == entrustNo:
                return entrust[self.curEntrustHeaderStateIndex]

        return None
    # 比较两组委托的状态
    def _compareEntrusts(self, entrusts, newEntrusts):
        """
            比较两组委托的状态
            虚函数，由基类调用
            @entrusts: old entrusts
            @newEntrusts: new entrusts
            @return: 委托状态变化，所有委托都完成
        """
        # 没有新的委托
        if newEntrusts is None:
            return False, False

        # 没有老委托，则是刚开始查询委托
        if entrusts is None:
            stateChange = True # 委托状态有没有跟新
            allDone = True# 所有委托都完成

            entrusts = newEntrusts# 没有老的委托，输入的就是新的

        else:
            stateChange = False
            allDone = True

        # compare state for each new entrust
        for newEntrust in newEntrusts:
            newEntrustNo = newEntrust[self.curEntrustHeaderNoIndex]
            newEntrustState = newEntrust[self.curEntrustHeaderStateIndex]

            entrustState = self._getEntrustState(newEntrustNo, entrusts)

            if entrustState != newEntrustState:# 新的委托状态和旧的不一样
                stateChange = True

            if newEntrustState not in ['已成', '已撤', '废单', '部撤']:
                allDone = False

        return stateChange, allDone

    # 子类实现
    def buy(self, code, name, price, volume):
        """
            @return: True - success without broker entrust ID
                     False - failed
                     broker entrust ID - success with broker entrust ID
        """
        raise NotImplementedError
    # 子类实现
    def sell(self, code, name, price, volume):
        """
            @return: True - success without broker entrust ID
                     False - failed
                     broker entrust ID - success with broker entrust ID
        """
        raise NotImplementedError