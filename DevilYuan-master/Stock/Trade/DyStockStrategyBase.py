from EventEngine.DyEvent import *

#
class DyStockStrategyState:
    running = 'sRunning'
    monitoring = 'sMonitoring'

    backTesting = 'sBackTesting'

    def __init__(self, *states):
        self._state = None

        self.add(*states)

    @property
    def state(self):
        if self._state is None:
            return '空'

        state = self._state.replace(self.running, '运行')# 换成后面的中文
        state = state.replace(self.monitoring, '监控')
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
        if self._state is None:
            if state is None:
                return True # 状态是空
            else:
                return False 

        if state in self._state:
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

    #相应的状态发送到事件引擎，包括运行以及其他状态的更改事件
    def checkState(self, state, strategyCls, eventEngine):
        if self.isState(state):
            return
        #那就添加状态，让其有状态
        self.add(state)

        if self._state == state:
            event = DyEvent(DyEventType.startStockCtaStrategy)#开始执行策略

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(self._state)
        else:
            event = DyEvent(DyEventType.changeStockCtaStrategyState)# 更改股票策略

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(*self._state.split('+'))# 
        #放到事件引擎中执行
        eventEngine.put(event)

    #解除状态，空状态的话结束策略，如果删了一个转太还不是空状态，换为另一种状态
    def uncheckState(self, state, strategyCls, eventEngine):
        if not self.isState(state):
            return

        self.remove(state)#状态对应

        if not self._state:#空状态，停止策略
            event = DyEvent(DyEventType.stopStockCtaStrategy)

            event.data['class'] = strategyCls
        else:
            event = DyEvent(DyEventType.changeStockCtaStrategyState)

            event.data['class'] = strategyCls
            event.data['state'] = DyStockStrategyState(self._state)

        eventEngine.put(event)
    # 我同时选择了 运行和监控的处理细节
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
    # 所有状态都是空的处理办法
    def uncheckAll(self, strategyCls, eventEngine):
        if self._state is None:
            return
        #状态设为空
        self._state = None
        #对应停止策略
        event = DyEvent(DyEventType.stopStockCtaStrategy)
        event.data['class'] = strategyCls

        eventEngine.put(event)


