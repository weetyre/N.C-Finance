import threading
import queue

from .DyEvent import *
#程威 12/17
#引擎编写总体思路，首先有六层，第一层事件层，有很多格子，每一列是一个看门人，是一个hand，每一个hand管理很多handler，管理很多羊群，最后这个单个羊，handler负责处理event
#第二层，就是这个大环境下他们的映射。
#第三层，专门为时间事件设计的特殊的守护者线程，这个线程按照interval 来动态注册解注册，第四层同样有他自己的映射。
#第五层最大环境的整体映射，eventMap，不管是不是时间类，都在里面，第六层就是所有事件都在event这个队列里。
#引擎可以理解为daboss，资源分发者，首先肯定给了好多event，给了hand数目，最后根据是否有已占用hand减少hand数目，进行合理分配，从此运行起来。
#最后调用start函数开始运行，只有一个timerhand，

class DyTimerHand(threading.Thread):
    def __init__(self, queue, eventEngine):
        super().__init__()

        self._intervals = {} # {interval: interval count}
        self._queue = queue
        self._eventEngine = eventEngine

    def run(self):
        while True:
            try:
                event = self._queue.get(block=True, timeout=1)
                interval = event.data

                # register event
                if event.type == DyEventType.register:
                    if interval not in self._intervals:
                        self._intervals[interval] = interval
                else: # unregister event
                    if interval in self._intervals:
                        del self._intervals[interval]
                
            except queue.Empty: # 1s time out
                for interval in self._intervals:
                    count = self._intervals[interval]

                    count -= 1

                    # trigger timer out event
                    if count == 0:
                        self._eventEngine.put(DyEvent(DyEventType.timer + str(interval)))

                        # new start
                        count = interval

                        if DyEventEngine.enableTimerLog:
                            print('Timer_%s'%interval)

                    self._intervals[interval] = count



class DyEventHand(threading.Thread):
    def __init__(self, queue):
        super().__init__()

        self._handlers = {} # {event type:[handlers]}
        self._queue = queue

    def run(self):
        while True:
            event = self._queue.get()

            if event.type == DyEventType.register:
                self._processRegisterEvent(event.data['type'], event.data['handler'])
            elif event.type == DyEventType.unregister:
                self._processUnregisterEvent(event.data['type'], event.data['handler'])
            else:
                self._processOtherEvent(event)
    #注册和解注册的目的就是添加函数映射，以及接触函数映射
    def _processRegisterEvent(self, type, handler):
        if type not in self._handlers:
            self._handlers[type] = []

        if handler not in self._handlers[type]:
            self._handlers[type].append(handler)

    def _processUnregisterEvent(self, type, handler):
        if type in self._handlers:
            if handler in self._handlers[type]:
                self._handlers[type].remove(handler)

                if not self._handlers[type]:
                    del self._handlers[type]
    #真正执行的在这里
    def _processOtherEvent(self, event):
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                handler(event)#handler 是具体的每一个函数


class DyEventEngine(threading.Thread):
    """
        事件引擎类

        非timer事件：
            三元组合（event type，handler，hand）标识一个事件监听。
            重复注册相同的事件监听（event type，handler，hand都相同），只有第一次注册生效。
            支持注销不存在的事件监听。

        timer事件：
            三元组合（handler，hand，timer interval）标识一个timer监听。
            重复注册相同的timer监听（handler，hand，timer interval都相同），只有第一次注册生效。
            也就是说，不同的timer interval，相同的handler和hand，是可以注册成功的。
            支持注销不存在的timer监听。
    """
    enableTimerLog = False


    def __init__(self, handNbr, timer=True):
        super().__init__()

        self._handNbr = handNbr

        # timer
        if timer:
            self._timerHandQueue = queue.Queue()
            self._timerHand = DyTimerHand(self._timerHandQueue, self)
        else:
            self._timerHandQueue = None
            self._timerHand = None

        self._timerMap = {} # {interval:{hand:[handlers]}}

        # hands类实例
        self._hands = []
        self._handQueues = [] # each hand maps to one element in list, [Queue()]

        # main data of event engine
        self._engineQueue = queue.Queue()
        self._eventMap = {} # which hand handles which event, {event type:{hand:[handlers]}}

        self._initHands()

    def _initHands(self):
        for i in range(self._handNbr):
            queue_ = queue.Queue()
            self._handQueues.append(queue_)#队列里加入了很多类得实例

            self._hands.append(DyEventHand(queue_))
    #倒数第二部run函数调用的，都把他们放到eventengine里面
        #事件相关的解注册以及注册
        #把他们想象成牧羊人，不同牧羊人养着不同的羊就行。
    def _processUnregister(self, data):
        """ @data: {'type':,'handler':, 'hand':}
        """
        type = data['type']
        handler = data['handler']#函数指针
        hand = data['hand']#类的实例

        event = DyEvent(DyEventType.unregister)
        event.data['type'] = type
        event.data['handler'] = handler

        # remove handler from event map
        if type in self._eventMap:
            if hand in self._eventMap[type]:
                if handler in self._eventMap[type][hand]:
                    self._eventMap[type][hand].remove(handler)

                    # unregister from corresponding hand
                    self._handQueues[hand].put(event)

                    if not self._eventMap[type][hand]:
                        del self._eventMap[type][hand]

                if not self._eventMap[type]:
                    del self._eventMap[type]

    def _processRegister(self, data):
        """ @data: {'type':,'handler':, 'hand':}#记住这是重点，每一个事件，会携带队列得hand的数字序号索引，以及相应的函数指针
        """
        type = data['type']
        handler = data['handler']
        hand = data['hand']
        #再次第二次建立event实例，也是注册类型，data里的type是具体的type
        event = DyEvent(DyEventType.register)
        event.data['type'] = type
        event.data['handler'] = handler

        # add to event map
        if type not in self._eventMap:
            self._eventMap[type] = {}

        if hand not in self._eventMap[type]:
            self._eventMap[type][hand] = []

        if handler not in self._eventMap[type][hand]:
            self._eventMap[type][hand].append(handler)

            # register to corresponding hand
            self._handQueues[hand].put(event)

    def _processRegisterTimer(self, data):
        # unpack
        interval = data['interval']
        handler = data['handler']
        hand = data['hand']

        # register timer event to corresponding hand
        self._processRegister(dict(type=DyEventType.timer + str(interval),
                                handler=handler,
                                hand=hand))

        # add to timer map
        if interval not in self._timerMap:
            self._timerMap[interval] = {}

            # register new interval to timer hand
            event = DyEvent(DyEventType.register)
            event.data = interval

            self._timerHandQueue.put(event)

        if hand not in self._timerMap[interval]:
            self._timerMap[interval][hand] = []

        if handler not in self._timerMap[interval][hand]:
            self._timerMap[interval][hand].append(handler)

    def _processUnregisterTimer(self, data):
        # unpack
        interval = data['interval']
        handler = data['handler']
        hand = data['hand']

        # unregister timer event from corresponding hand
        self._processUnregister(dict(type=DyEventType.timer + str(interval),
                                handler=handler,
                                hand=hand))

        # remove handler from timer map
        if interval in self._timerMap:
            if hand in self._timerMap[interval]:
                if handler in self._timerMap[interval][hand]:
                    self._timerMap[interval][hand].remove(handler)

                    if not self._timerMap[interval][hand]: # empty
                        del self._timerMap[interval][hand]

                if not self._timerMap[interval]: # empty
                    del self._timerMap[interval]

                    # no any handler for this timer, so unregister interval from timer hand
                    event = DyEvent(DyEventType.unregister)
                    event.data = interval

                    self._timerHandQueue.put(event)
    #这是倒数第二步，从eventengine取出来
    def run(self):
        while True:
            event = self._engineQueue.get()

            if event.type == DyEventType.registerTimer:
                self._processRegisterTimer(event.data)

            elif event.type == DyEventType.register:
                self._processRegister(event.data)

            elif event.type == DyEventType.unregisterTimer:
                self._processUnregisterTimer(event.data)

            elif event.type == DyEventType.unregister:
                self._processUnregister(event.data)
            # 通过应用，直接交互过来的事件，比如点击回测
            else: # event for applications
                hands = self._eventMap.get(event.type)
                if hands is not None:
                    for hand in hands: # hand which is listening this event
                        self._handQueues[hand].put(event)# 又放到最外的类，最终放到event线程那个类里面
    #第一步运行4组，放入eventengine（一般外部调用第一）
    def registerTimer(self, handler, hand=None, interval=1):
        if hand is None:
            hand = self._handNbr - 1

        event = DyEvent(DyEventType.registerTimer)
        event.data = dict(hand=hand, handler=handler, interval=interval)#这句话是重点

        self.put(event)

    def register(self, type, handler, hand=None):
        if hand is None:
            hand = self._handNbr - 1

        #首先evnt外面的type属性他是一个注册的事件，但是data这个字典里，type是对应具体的事件类型（列如，单进度条事件）
        event = DyEvent(DyEventType.register)
        event.data = dict(type=type, handler=handler, hand=hand)#这个hand的确是个数字，因为这是number-1下来的

        self.put(event)

    def unregister(self, type, handler, hand=None):
        if hand is None:
            hand = self._handNbr - 1

        event = DyEvent(DyEventType.unregister)
        event.data = dict(type=type, handler=handler, hand=hand)

        self.put(event)

    def unregisterTimer(self, handler, hand=None, interval=1):
        if hand is None:
            hand = self._handNbr - 1

        event = DyEvent(DyEventType.unregisterTimer)
        event.data = dict(hand=hand, handler=handler, interval=interval)

        self.put(event)
    #外部调用第二，他会把具体注册的事件类型放进去
    def put(self, event):
        self._engineQueue.put(event)

    def stop(self):
        pass
    #第二：start，外部功能模块在实例化引擎的时候，第二步就是start
    def start(self):
        for hand in self._hands:
            hand.start()# 每一个事件线程start

        if self._timerHand:
            self._timerHand.start()

        super().start()# 最后start 自己的run函数


class DyDummyEventEngine:
    def __init__(self):
        pass

    def put(self, event):
        pass
