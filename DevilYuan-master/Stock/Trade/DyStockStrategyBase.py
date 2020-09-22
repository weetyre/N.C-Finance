from EventEngine.DyEvent import *

# 股票策略状态
class DyStockStrategyState:
    running = 'sRunning'
    monitoring = 'sMonitoring'

    backTesting = 'sBackTesting'

    def __init__(self, *states):
        self._state = None

        self.add(*states)

    @property# 调用这个负责转成中文字符串
    def state(self):
        if self._state is None:
            return '空'

        state = self._state.replace(self.running, '运行')# 换成后面的中文
        state = state.replace(self.monitoring, '监控')# 自己调用自己，转成中文
        state = state.replace(self.backTesting, '回测')

        return state
    #状态字符串加起来
    def add(self, *states):
        if self._state:
            self._state +=  ('+' + '+'.join(states))
        else:
            if states:
                self._state = '+'.join(states)
    #
    def isState(self, state):
        if self._state is None:#
            if state is None:
                return True # 状态是空
            else:
                return False 

        if state in self._state:# 只要在这个字符串里就T
            return True

        return False
    #移除状态
    def remove(self, *states):
        if not self._state: return

        curStates = self._state.split('+')

        for state in states:
            if state in curStates:
                curStates.remove(state)

        curStates = '+'.join(curStates)

        if not curStates:# 如果有其他状态，那么保留其他状态，如果没有，就是空
            curStates = None

        self._state = curStates

    #相应的状态发送到事件引擎，包括运行以及其他状态的更改事件#
    def checkState(self, state, strategyCls, eventEngine):
        if self.isState(state):# 本身是这个状态
            return
        #不是这个状态，那就添加状态，让其有状态
        self.add(state)

        if self._state == state:# 在这里只能是运行或者是监控（因为本来这个策略如果是监控状态，再加一个运行，那就是状态改变）
            event = DyEvent(DyEventType.startStockCtaStrategy)#开始执行策略

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(self._state)
        else:
            event = DyEvent(DyEventType.changeStockCtaStrategyState)# 更改股票策略

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(*self._state.split('+'))# 运行监控，不同顺序
        #放到事件引擎中执行
        eventEngine.put(event)

    #解除状态，空状态的话结束策略，如果删了一个转太还不是空状态，换为另一种状态
    def uncheckState(self, state, strategyCls, eventEngine):
        if not self.isState(state):# 首先确保存在状态
            return

        self.remove(state)#状态对应

        if not self._state:#空状态，停止策略
            event = DyEvent(DyEventType.stopStockCtaStrategy)

            event.data['class'] = strategyCls
        else:
            event = DyEvent(DyEventType.changeStockCtaStrategyState)# 否则改变状态时间

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(self._state)# 剩余的那个状态传入

        eventEngine.put(event)
    # 同时选择 运行和监控的处理细节
    def checkAll(self, strategyCls, eventEngine):
        """ check '运行' 和 '监控' """

        if self.isState(DyStockStrategyState.running) and self.isState(DyStockStrategyState.monitoring):
            return # 如果同时处于这两种状态，不处理
        
        if self._state is None:#空，同时添加两个状态
            event = DyEvent(DyEventType.startStockCtaStrategy)

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(DyStockStrategyState.running, DyStockStrategyState.monitoring)# 新生成一个

            self.add(DyStockStrategyState.running, DyStockStrategyState.monitoring) # 原有状态变化，方便处理

        else:
            if self.isState(DyStockStrategyState.running):
                self.add(DyStockStrategyState.monitoring)
            else:
                self.add(DyStockStrategyState.running)

            event = DyEvent(DyEventType.changeStockCtaStrategyState)#更改状态事件

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(DyStockStrategyState.monitoring, DyStockStrategyState.running)

        eventEngine.put(event)
    # 撤销所有状态后处理
    def uncheckAll(self, strategyCls, eventEngine):
        if self._state is None:
            return
        #状态设为空
        self._state = None
        #对应停止策略
        event = DyEvent(DyEventType.stopStockCtaStrategy)
        event.data['class'] = strategyCls

        eventEngine.put(event)


