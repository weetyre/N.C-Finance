import os

from Stock import DynamicLoadStrategyFields

# 策略动态载入
# dynamically load strategies from Stock/Trade/Strategy
__pathList = os.path.dirname(__file__).split(os.path.sep)
__stratgyPath = os.path.sep.join(__pathList[:-2] + ['Strategy'])
# 股票策略表映射
DyStockTradeStrategyClsMap = {}
DyStockTradeStrategyWidgetAutoFields = DynamicLoadStrategyFields(__stratgyPath, 'Stock.Trade.Strategy', DyStockTradeStrategyClsMap) # 返回策略类集 [[strategyCls],[.]..]
