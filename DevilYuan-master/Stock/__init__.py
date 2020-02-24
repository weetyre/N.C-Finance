# Check user package intelligently
from Stock.Common.DyStockCommon import DyStockCommon

try:
    from WindPy import *
except ImportError:
    if DyStockCommon.WindPyInstalled:
        print("DevilYuan-Warning: Import WindPy error, switch default data source of stock history days to TuShare!")
        DyStockCommon.WindPyInstalled = False
#在开始的时候先验证Wind包是否安装，如果没有安装，默认数据源转到Tushare

import os
import importlib


# dynamically load strategies from specific package, like 'Stock.Trade.Strategy'
def __loadStrategies(dir, packageCommonPrefix, strategyClsMap, onlyDir=True):#递归的方式载入
    fields = []
    for root, dirs, files in os.walk(dir):
        for dirName in dirs:
            if dirName[:2] == '__': # python internal dirs
                continue

            dirFields = []
            fields.append(dirFields)

            dirFields.append(dirName)# 全是下面的目录，继续往下走
            retFields = __loadStrategies(os.path.sep.join([dir, dirName]), packageCommonPrefix, strategyClsMap, onlyDir=False)
            if retFields:
                dirFields.append(retFields)

        if not onlyDir:#现在进去就开始对py策略文件进行载入
            packageName = dir.replace(os.path.sep, '.')# 包名分开
            packagePrefixStart = packageName.index(packageCommonPrefix)
            packagePrefix = packageName[packagePrefixStart:]
            #递归文件
            for file in files:
                if file == '__init__.py' or file[-3:] != '.py':
                    continue

                module = importlib.import_module('{}.{}'.format(packagePrefix, file[:-3]))#

                strategyClsName = file[:-3]#除去 .py
                strategyCls = module.__getattribute__(strategyClsName) # 根据类名，取出类

                strategyClsMap[strategyClsName] = strategyCls # 策略类名，策略类

                fields.append([strategyCls]) # strategy class

        break

    return fields # 返回的是策略类

#根据本地目录开始载入
def DynamicLoadStrategyFields(dir, packageCommonPrefix, strategyClsMap):
    """
        @strategyClsMap: {strategy class name: strategy class}, out parameter
        @packageCommonPrefix : 'Stock.Trade.Strategy'
    """
    return __loadStrategies(dir, packageCommonPrefix, strategyClsMap, onlyDir=True)