import threading
import requests

from .wxbot import WXBot

from DyCommon.DyCommon import *
from EventEngine.DyEvent import *
from ..DyStockTradeCommon import *

# 微信机器人类
class DyStockTradeWxBot(WXBot):# 他是继承于主微信机器人
    def __init__(self, eventEngine, info):
        super().__init__()

        self._eventEngine = eventEngine
        self._info = info

        self.DEBUG = False
    # 处理信息，决定发送那个信息（1，2，3）
    def handle_msg_all(self, msg):
        try:
            if msg['user']['name'] == 'self':# 发给自己的
                event = DyEvent(DyEventType.wxQueryStockStrategy) # 微信查询股票策略实时信息
                event.data = msg['content']['data']# 获取消息内容（1，2，3）

                self._eventEngine.put(event)
        except:
            pass
    # 最后
    def send(self, msg):# 后面是整合的数据，并且等待发送信息
        try:
            # 发送给自己, 目前会失败
            #self.send_msg_by_uid(msg, self.my_account['UserName'])# 到此发送结束
            # filehelper
            self.send_msg_by_uid(msg, "filehelper")  # 到此发送结束
        except:
            pass

# 股票交易微信主引擎
class DyStockTradeWxEngine(object):
    """
        使用WXBot进行实盘策略信号提醒
    """
    scKey = None # 通过配置界面进行配置

    # 初始化
    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._wxBot = None # 实例微信机器人
        self._isStop = True# 默认停止

        self._latestStrategyData = {} # {strategy name: (strategy class, time, data)}
        self._latestMarketStrengthData = None

        self._pushAction = None # 发给WX的Action

        self._registerEvent()
    # 注册相关事件
    def _registerEvent(self):
        self._eventEngine.register(DyEventType.startStockCtaStrategy, self._startStockCtaStrategyHandler, DyStockTradeEventHandType.wxEngine)
        self._eventEngine.register(DyEventType.stopStockCtaStrategy, self._stopStockCtaStrategyHandler, DyStockTradeEventHandType.wxEngine)

        self._eventEngine.register(DyEventType.startStockWx, self._startStockWxHandler, DyStockTradeEventHandType.wxEngine)
        self._eventEngine.register(DyEventType.stopStockWx, self._stopStockWxHandler, DyStockTradeEventHandType.wxEngine)

        self._eventEngine.register(DyEventType.wxQueryStockStrategy, self._wxQueryStockStrategyHandler, DyStockTradeEventHandType.wxEngine)
        self._eventEngine.register(DyEventType.sendStockTestWx, self._sendStockTestWxHandler, DyStockTradeEventHandType.wxEngine)

        self._eventEngine.register(DyEventType.stockMarketStrengthUpdateFromUi, self._stockMarketStrengthUpdateFromUiHandler, DyStockTradeEventHandType.wxEngine)

        self._eventEngine.register(DyEventType.stockStrategyOnOpen, self._stockStrategyOnOpenHandler, DyStockTradeEventHandType.wxEngine)
    # CTA策略开始处理事件
    def _startStockCtaStrategyHandler(self, event):
        strategyCls = event.data['class'] # 返回策略类

        self._eventEngine.register(DyEventType.stockMarketMonitorUi + strategyCls.name, self._stockMarketMonitorUiHandler, DyStockTradeEventHandType.wxEngine)

        self._latestStrategyData[strategyCls.name] = None
    # 停止 CTA 策略
    def _stopStockCtaStrategyHandler(self, event):
        strategyCls = event.data['class']

        self._eventEngine.unregister(DyEventType.stockMarketMonitorUi + strategyCls.name, self._stockMarketMonitorUiHandler, DyStockTradeEventHandType.wxEngine)

        del self._latestStrategyData[strategyCls.name]# 顺便删了
    # 开始全新的微信机器人（通过一个线程来启动）
    def _startWxBot(self):
        """
            全新开始一个WXBot
        """
        self._wxBotThread = threading.Thread(target=self._wxBotThreadHandler, args=(self._eventEngine, self._info))
        self._wxBotThread.start()
    # 开始微信提醒就会到这里
    def _startStockWxHandler(self, event):
        self._isStop = False# 没有停止

        if self._wxBot is not None:
            return

        self._startWxBot()# 开始微信机器人
    # 微信机器人开始的线程
    def _wxBotThreadHandler(self, eventEngine, info):
        self._wxBot = DyStockTradeWxBot(eventEngine, info)

        self._wxBot.run()# 先开始登录获取必要的信息
    # 关闭微信提醒，直接Stop即可
    def _stopStockWxHandler(self, event):
        self._isStop = True
    # 发送到微信
    def _sendWx(self, msg):
        """
            向文件传输助手发送微信
        """
        self._wxBot.send(msg)
    # 微信取完数据之后发送
    def _send(self, strategyCls, time, name, data, isMsgList=False, pureMsg=False):
        """
            @time: 本地时间
            @name: @data的名字
            @data: [[x, y]] or [WX message]
            @isMsgList: @data format is list of WX message(string)
        """
        if pureMsg:# 纯信息
            text = '{0}[{1}]:\n{2}-{3}'.format(strategyCls.chName, time.strftime('%H:%M:%S'), name, data)

            # sent to WX
            self._sendWx(text)
        else:
            if isMsgList:
                # send header
                text = '{0}[{1}]:\n{2}-'.format(strategyCls.chName, time.strftime('%H:%M:%S'), name)
                self._sendWx(text)

                # send body
                for text in data:
                    self._sendWx(text)

            else:
                # 只显示两位小数
                newData = []
                for row in data:
                    newData.append([float('%.2f'%x) if isinstance(x, float) else x for x in row])

                text = '{0}[{1}]:\n{2}-{3}'.format(strategyCls.chName, time.strftime('%H:%M:%S'), name, newData)

                # sent to WX
                self._sendWx(text)
    # 最后调用这个函数进行发送
    def _sendWxViaFt(self, title, msg):
        """
            通过server酱（方糖）推送
        """
        if not self.scKey:
            return

        data = {'text': title,
                'desp': msg
                }
        requests.post('http://sc.ftqq.com/{}.send'.format(self.scKey), data=data)
    # 通过server酱（方糖）推送
    def _sendViaFt(self, strategyCls, time, name, data, isMsgList=False, pureMsg=False):
        """
            通过server酱（方糖）推送
            @time: 本地时间
            @name: @data的名字
            @data: [[x, y]] or [WX message]
            @isMsgList: @data format is list of WX message(string)
        """
        if pureMsg:
            text = '{0}[{1}]:\n{2}-{3}'.format(strategyCls.chName, time.strftime('%H:%M:%S'), name, data)

            # sent to WX
            self._sendWxViaFt(strategyCls.chName, text)
        else:
            if isMsgList:
                # send header
                text = '{0}[{1}]:\n{2}-'.format(strategyCls.chName, time.strftime('%H:%M:%S'), name)
                self._sendWxViaFt(strategyCls.chName, text)

                # send body
                for text in data:
                    self._sendWxViaFt(strategyCls.chName, text)

            else:
                # 只显示两位小数
                newData = []
                for row in data:
                    newData.append([float('%.2f'%x) if isinstance(x, float) else x for x in row])

                text = '{0}[{1}]:\n{2}-{3}'.format(strategyCls.chName, time.strftime('%H:%M:%S'), name, newData)

                # sent to WX
                self._sendWxViaFt(strategyCls.chName, text)
    # 股票行情界面相关数据更新处理
    def _stockMarketMonitorUiHandler(self, event):
        if self._isStop:
            return

        if self._wxBot is None:
            return

        strategyCls = event.data['class']

        # save strategy latest data
        if 'data' in event.data:# 数据界面
            data = event.data['data']['data']

            if strategyCls.name in self._latestStrategyData:# 刚开始Start的时候就已经赋值Key，在这里赋值数据
                self._latestStrategyData[strategyCls.name] = (strategyCls, datetime.now(), '数据', data)
        # 信息界面
        # check if there's signal or operation of strategy
        if 'ind' in event.data:
            if 'signalDetails' in event.data['ind']:
                signalDetails = event.data['ind']['signalDetails']
                # 通过两个发送函数发送
                self._send(strategyCls, datetime.now(), '信号明细', signalDetails)
                self._sendViaFt(strategyCls, datetime.now(), '信号明细', signalDetails)

            if 'op' in event.data['ind']:
                op = event.data['ind']['op']

                self._send(strategyCls, datetime.now(), '操作', op)
                self._sendViaFt(strategyCls, datetime.now(), '操作', op)
    # 发送测试微信函数
    def _sendStockTestWxHandler(self, event):
        if self._isStop:
            return

        if self._wxBot is None:
            return

        text = event.data

        # sent to WX
        self._sendWx(text)
        self._sendWxViaFt("测试消息", text)
    # # 来自于UI的股票市场强度更新事件
    def _stockMarketStrengthUpdateFromUiHandler(self, event):
        """
            处理来自于UI的市场强度更新事件
        """
        self._latestMarketStrengthData = event.data
    # 微信委托买入
    def _stockMarketTicksHandler(self, event):
        if self._pushAction is None:# '买入'
            return

        ticks = event.data
        # 只能是这个类的数据，否则返回空
        strategyData = self._latestStrategyData.get('DyST_IndexMeanReversion')# 指数均线反转获取
        if strategyData is None:
            return

        strategyCls = strategyData[0]# 策略类

        tick = ticks.get(strategyCls.targetCode)# 策略的目标代码
        if tick is None:
            return

        # event
        event = DyEvent(DyEventType.stockStrategyManualBuy)# 通过UI手动买入（和tab右键买入的过程是一样的）
        event.data['class'] = strategyCls
        event.data['tick'] = tick# 买入的是策略监控的股票
        event.data['volume'] = 100

        event.data['price'] = round(tick.preClose * 0.92, 3)# 价格为92% 测试用

        self._eventEngine.put(event)

        self._info.print('通过WX委托买入{0}, {1}股, 价格{2}'.format(tick.name, event.data['volume'], event.data['price']), DyLogData.ind1)

        # sent to WX
        self._sendWx('委托买入{0}, {1}股, 价格{2}'.format(tick.name, event.data['volume'], event.data['price']))

        # clear
        self._pushAction = None# 清除，解注册这个微信买入测试函数
        self._eventEngine.unregister(DyEventType.stockMarketTicks, self._stockMarketTicksHandler, DyStockTradeEventHandType.wxEngine)
    # 查询市场强度，且发送
    def _queryMarketStrength(self):
        if self._latestMarketStrengthData is None:
            return

        # assemble to text
        text = ''
        for name, value in self._latestMarketStrengthData:
            if text:
                text += '\n'

            text += '{0}: {1}'.format(name, '' if value is None else value)

        # sent to WX
        self._sendWx(text)
    # 查询策略行情数据且发送
    def _queryStrategyData(self):
        for _, group in self._latestStrategyData.items():#  {strategy name: (strategy class, time, data)}
            if group is None:
                continue

            strategyCls, time, name, data = group
            if not strategyCls.enableQuery:# 策略是否支持微信查询请求
                continue

            if hasattr(strategyCls, 'data2Msg'):# 有没有这个函数
                isMsgList = True
                data = strategyCls.data2Msg(data)# 将推送给UI的data转成消息列表，这样可以推送给QQ或者微信
            else:
                isMsgList = False
                data = [data[-1]]# 取最后

            self._send(strategyCls, time, name, data, isMsgList)
    # 微信查询股票策略实时信息
    def _wxQueryStockStrategyHandler(self, event):
        """
            WX远程请求市场和策略相关的数据
            @message: 1, 2, 3
        """
        if self._isStop:
            return

        if self._wxBot is None:
            return

        message = event.data

        if message == '1': # 策略行情数据
            self._queryStrategyData()# 内部调用发送（相当于一个交互的功能）
        
        elif message == '2': # 市场强度
            self._queryMarketStrength()# 内部调用发送（相当于一个交互的功能）

        elif message == '3': # 测试用，买入指数均值回归策略的标的
            self._pushAction = '买入'
            self._eventEngine.register(DyEventType.stockMarketTicks, self._stockMarketTicksHandler, DyStockTradeEventHandType.wxEngine)# 3
    # 策略开盘事件
    def _stockStrategyOnOpenHandler(self, event):
        if self._isStop:
            return

        if self._wxBot is None:
            return

        strategyCls = event.data['class']
        msg = event.data['msg']

        self._send(strategyCls, datetime.now(), 'OnOpen', msg, pureMsg=True)# 这里是纯消息
        self._sendViaFt(strategyCls, datetime.now(), 'OnOpen', msg, pureMsg=True)
