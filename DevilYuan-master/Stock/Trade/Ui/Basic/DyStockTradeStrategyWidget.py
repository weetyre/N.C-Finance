from DyCommon.Ui.DyTreeWidget import *
from EventEngine.DyEvent import *
from ...DyStockStrategyBase import *

from . import DyStockTradeStrategyWidgetAutoFields


class DyStockTradeStrategyWidget(DyTreeWidget):
    
    strategyFields = DyStockTradeStrategyWidgetAutoFields # 策略类


    def __init__(self, eventEngine):
        self._strategies = {} # {strategy chName: [state, strategy class]}
        newFields = self._transform(self.__class__.strategyFields) # 调用类属性
        
        super().__init__(newFields)
        self.collapse('Obsolete')

        self._eventEngine = eventEngine

        # At last, set tooltip of each strategy to which broker it uses
        for chName, (_, strategyCls) in self._strategies.items():
            itemList =  self.findItems(chName, Qt.MatchExactly|Qt.MatchRecursive, 0)
            assert len(itemList) == 1
            itemList[0].setToolTip(0, 'broker={}'.format(strategyCls.broker))#鼠标悬浮到策略上，会弹出文本

    def on_itemClicked(self, item, column):
        super(DyStockTradeStrategyWidget, self).on_itemClicked(item, column)

        if item.checkState(0) == Qt.Checked:
            pass
    #
    def on_itemChanged(self, item, column):#从这里来触发是否放入事件引擎中

        text = item.text(0)#获取策略名称

        if item.checkState(0) == Qt.Checked:

            if text in self._strategies:
                strategyState, strategyCls = self._strategies[text]
                strategyState.checkAll(strategyCls, self._eventEngine) 
            #如果点击的是子目录
            elif text == '运行' or text == '监控':
                strategyState, strategyCls = self._strategies[item.parent().text(0)]

                state = self._getStateByText(text)
                strategyState.checkState(state, strategyCls, self._eventEngine)
        else:

            if text in self._strategies:
                strategyState, strategyCls = self._strategies[text]
                strategyState.uncheckAll(strategyCls, self._eventEngine)#撤销所有策略

            elif text == '运行' or text == '监控':
                strategyState, strategyCls = self._strategies[item.parent().text(0)]

                state = self._getStateByText(text)
                strategyState.uncheckState(state, strategyCls, self._eventEngine)#撤销单状态

        super().on_itemChanged(item, column)#反复确认
    #通过文字来获取上下文状态
    def _getStateByText(self, text):
        if text == '运行':
            return DyStockStrategyState.running

        return DyStockStrategyState.monitoring
    
    #转换成新的目录树结构
    def _transform(self, fields):
        newFields = []
        for field in fields:
            if isinstance(field, list):# 证明上级还有东西
                retFields = self._transform(field) # 递归转换
                if retFields:
                    newFields.append(retFields)
            else:#递归到真正的类
                if hasattr(field,  'chName'):
                    if field.__name__[-3:] != '_BT': # ignore pure backtesting strategy
                        newFields.append(field.chName)
                        newFields.append(['运行'])
                        newFields.append(['监控'])

                        self._strategies[field.chName] = [DyStockStrategyState(), field] # 添加映射，默认状态空none
                else:
                    newFields.append(field) # 为了递归

        return newFields #3个参数构成
