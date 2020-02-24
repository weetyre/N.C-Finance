from PyQt5 import QtCore
from PyQt5.QtWidgets import QTabWidget

from .DyStockSelectStrategyParamWidget import *

#选择参数组件（加一个表格放在这个TAB里面）
class DyStockSelectParamWidget(QTabWidget):

    def __init__(self):
        super().__init__()

        self._strategyParamWidgets = {}

        self.setTabsClosable(True)# 可以通过关闭按钮关闭
        self.tabCloseRequested.connect(self._closeTab)

    def set(self, strategyName, paramters, tooltips=None):
        if strategyName not in self._strategyParamWidgets:
            widget = DyStockSelectStrategyParamWidget()#就是一个表格放到这个TAB里面了
            self.addTab(widget, strategyName)#添加

            # save
            self._strategyParamWidgets[strategyName] = widget

            self._strategyParamWidgets[strategyName].set(paramters)#设置列名
            self._strategyParamWidgets[strategyName].setToolTip(tooltips)#设置提示

        self.setCurrentWidget(self._strategyParamWidgets[strategyName])#设置当前的组件
    #获得里面的参数
    def get(self, strategyName):
        return self._strategyParamWidgets[strategyName].get()
    #关闭这个标签
    def _closeTab(self, index):
        tabName = self.tabText(index)

        param = self._strategyParamWidgets[tabName].get()
        self._strategyWidget.uncheckStrategy(tabName, param)#接触注册这个策略，且不打勾

        del self._strategyParamWidgets[tabName]#删除这个组件

        self.removeTab(index)#彻底删除

    def setStrategyWidget(self, strategyWidget):
        self._strategyWidget = strategyWidget

