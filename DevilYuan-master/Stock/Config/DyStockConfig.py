import os
import json
import copy

from DyCommon.DyCommon import DyCommon
from Stock.Common.DyStockCommon import DyStockCommon
from ..Data.Engine.DyStockMongoDbEngine import DyStockMongoDbEngine
from ..Trade.WeChat.DyStockTradeWxEngine import DyStockTradeWxEngine
from ..Trade.Broker.YhNew.YhTrader import YhTrader
from ..Trade.Broker.Ths.ThsTrader import ThsTrader
from ..Data.Gateway.DyStockDataGateway import DyStockDataGateway

# 股票配置类
class DyStockConfig(object):
    """
        Read configs from files and then set to corresponding variables
    """

    defaultMongoDb = {"Connection": {"Host": "localhost", "Port": 27017},
                      "CommonDays": {
                          "Wind": {
                              "stockCommonDb": 'stockCommonDb',
                              'tradeDayTableName': "tradeDayTable",
                              'codeTableName': "codeTable",
                              'stockDaysDb': 'stockDaysDb'
                              },
                          "TuShare": {
                              "stockCommonDb": 'stockCommonDbTuShare',
                              'tradeDayTableName': "tradeDayTableTuShare",
                              'codeTableName': "codeTableTuShare",
                              'stockDaysDb': 'stockDaysDbTuShare'
                              }
                          },
                      "Ticks": {"db": 'stockTicksDb'}
                      }

    defaultWxScKey = {"WxScKey": ""}

    defaultAccount = {"Ths": {"Account": "", "Password": "", "Exe": r"C:\Program Files\同花顺\xiadan.exe"},
                      "Yh": {"Account": "", "Password": "", "Exe": r"C:\Program Files\中国银河证券双子星3.2\Binarystar.exe"},
                      }

    defaultTradeDaysMode = {"tradeDaysMode": "Verify"}

    defaultTuShareDaysInterval = {"interval": 0}
    defaultTuShareProDaysInterval = {"interval": 0}

    #获取默认的数据源
    def getDefaultHistDaysDataSource():
        if DyStockCommon.WindPyInstalled:
            return {"Wind": True, "TuShare": False}

        return {"Wind": False, "TuShare": True}

    def _configStockHistDaysDataSource():
        file = DyStockConfig.getStockHistDaysDataSourceFileName()#文件名

        # open
        try:
            with open(file) as f:
                data = json.load(f)
        except:
            data = DyStockConfig.getDefaultHistDaysDataSource()#没有此文件读取默认数据源

        DyStockConfig.configStockHistDaysDataSource(data)

    def configStockHistDaysDataSource(data):
        DyStockCommon.defaultHistDaysDataSource = []# 根据是否为空来实现默认数据源
        if data.get('Wind'):
            DyStockCommon.defaultHistDaysDataSource.append('Wind')

        if data.get('TuShare'):
            DyStockCommon.defaultHistDaysDataSource.append('TuShare')
    #调用Dycommon,创建一个文件夹，返回路径，然后在返回文件名
    def getStockHistDaysDataSourceFileName():
        path = DyCommon.createPath('Stock/User/Config/Common')
        file = os.path.join(path, 'DyStockHistDaysDataSource.json')

        return file
    #配置TusharePro相关东西
    def _configStockHistDaysTuSharePro():
        file = DyStockConfig.getStockHistDaysTuShareProFileName()

        # open
        try:
            with open(file) as f:
                data = json.load(f)
        except:
            data = DyStockConfig.getDefaultHistDaysTuSharePro()

        DyStockConfig.configStockHistDaysTuSharePro(data)

    def configStockHistDaysTuSharePro(data):
        DyStockCommon.useTuSharePro = False
        DyStockCommon.tuShareProToken = None
        #如果为T，使用它，并且设置Token
        if data.get('TuSharePro'):
            DyStockCommon.useTuSharePro = True

        DyStockCommon.tuShareProToken = data.get('Token')
    #获取TosharePro配置文件
    def getStockHistDaysTuShareProFileName():
        path = DyCommon.createPath('Stock/User/Config/Common')
        file = os.path.join(path, 'DyStockHistDaysTuSharePro.json')

        return file
    #默认不用Pro,且不显示Token
    def getDefaultHistDaysTuSharePro():
        return {'TuSharePro': False, 'ShowToken': False}

    def _configStockMongoDb():
        file = DyStockConfig.getStockMongoDbFileName()

        # open
        try:
            with open(file) as f:
                data = json.load(f)
        except:
            data = DyStockConfig.defaultMongoDb

        DyStockConfig.configStockMongoDb(data)
    #设置IP port 和相应数据库名字
    def configStockMongoDb(data):
        DyStockMongoDbEngine.host = data['Connection']['Host']
        DyStockMongoDbEngine.port = data['Connection']['Port']

        # Wind
        DyStockMongoDbEngine.stockCommonDb = data["CommonDays"]["Wind"]['stockCommonDb']
        DyStockMongoDbEngine.tradeDayTableName = data["CommonDays"]["Wind"]['tradeDayTableName']
        DyStockMongoDbEngine.codeTableName = data["CommonDays"]["Wind"]['codeTableName']

        DyStockMongoDbEngine.stockDaysDb = data["CommonDays"]["Wind"]['stockDaysDb']

        # TuShare
        DyStockMongoDbEngine.stockCommonDbTuShare = data["CommonDays"]["TuShare"]['stockCommonDb']
        DyStockMongoDbEngine.tradeDayTableNameTuShare = data["CommonDays"]["TuShare"]['tradeDayTableName']
        DyStockMongoDbEngine.codeTableNameTuShare = data["CommonDays"]["TuShare"]['codeTableName']

        DyStockMongoDbEngine.stockDaysDbTuShare = data["CommonDays"]["TuShare"]['stockDaysDb']

        # ticks
        DyStockMongoDbEngine.stockTicksDb = data["Ticks"]["db"]
    #拿到StockMongoDb的配置文件名
    def getStockMongoDbFileName():
        path = DyCommon.createPath('Stock/User/Config/Common')
        file = os.path.join(path, 'DyStockMongoDb.json')

        return file

    def _configStockWxScKey():
        file = DyStockConfig.getStockWxScKeyFileName()

        # open
        try:
            with open(file) as f:
                data = json.load(f)
        except:
            data = DyStockConfig.defaultWxScKey

        DyStockConfig.configStockWxScKey(data)
    #配置微信密钥名
    def configStockWxScKey(data):
        DyStockTradeWxEngine.scKey = data["WxScKey"]
    #创建微信密钥文件名
    def getStockWxScKeyFileName():
        path = DyCommon.createPath('Stock/User/Config/Trade')
        file = os.path.join(path, 'DyStockWxScKey.json')

        return file
    #配置股票账户
    def _configStockAccount():
        file = DyStockConfig.getStockAccountFileName()

        # open
        try:
            with open(file) as f:
                data = json.load(f)
        except:
            data = DyStockConfig.defaultAccount

        DyStockConfig.configStockAccount(data)

    def configStockAccount(data):
        YhTrader.account = data["Yh"]["Account"]
        YhTrader.password = data["Yh"]["Password"]
        YhTrader.exePath = data["Yh"]["Exe"]

        ThsTrader.exePath = data["Ths"]["Exe"]
    #获取账户文件名
    def getStockAccountFileName():
        path = DyCommon.createPath('Stock/User/Config/Trade')
        file = os.path.join(path, 'DyStockAccount.json')

        return file

    def _configStockTradeDaysMode():
        file = DyStockConfig.getStockTradeDaysModeFileName()

        # open
        try:
            with open(file) as f:
                data = json.load(f)
        except:
            data = DyStockConfig.defaultTradeDaysMode

        DyStockConfig.configStockTradeDaysMode(data)
    #配置交易日模式
    def configStockTradeDaysMode(data):
        DyStockDataGateway.tradeDaysMode = data["tradeDaysMode"]
    #获取交易日模式文件名
    def getStockTradeDaysModeFileName():
        path = DyCommon.createPath('Stock/User/Config/Common')
        file = os.path.join(path, 'DyStockTradeDaysMode.json')

        return file
    #配置Tushare的Interval
    def _configStockTuShareDaysInterval():
        file = DyStockConfig.getStockTuShareDaysIntervalFileName()

        # open
        try:
            with open(file) as f:
                data = json.load(f)
        except:
            data = DyStockConfig.defaultTuShareDaysInterval

        DyStockConfig.configStockTuShareDaysInterval(data)
    #配置interval
    def configStockTuShareDaysInterval(data):
        DyStockDataGateway.tuShareDaysSleepTimeConst = data["interval"]
    #获取Tushare获取日之间的间隔文件名
    def getStockTuShareDaysIntervalFileName():
        path = DyCommon.createPath('Stock/User/Config/Common')
        file = os.path.join(path, 'DyStockTuShareDaysInterval.json')

        return file
    #配置proInterval
    def _configStockTuShareProDaysInterval():
        file = DyStockConfig.getStockTuShareProDaysIntervalFileName()

        # open
        try:
            with open(file) as f:
                data = json.load(f)
        except:
            data = DyStockConfig.defaultTuShareProDaysInterval

        DyStockConfig.configStockTuShareProDaysInterval(data)
    #设置Interval
    def configStockTuShareProDaysInterval(data):
        DyStockDataGateway.tuShareProDaysSleepTimeConst = data["interval"]
    #获取Interval名
    def getStockTuShareProDaysIntervalFileName():
        path = DyCommon.createPath('Stock/User/Config/Common')
        file = os.path.join(path, 'DyStockTuShareProDaysInterval.json')

        return file
    #总配置函数
    def config():
        DyStockConfig._configStockHistDaysDataSource() # first
        DyStockConfig._configStockHistDaysTuSharePro()
        DyStockConfig._configStockTradeDaysMode()
        DyStockConfig._configStockTuShareDaysInterval()
        DyStockConfig._configStockTuShareProDaysInterval()
        DyStockConfig._configStockMongoDb()
        DyStockConfig._configStockWxScKey()
        DyStockConfig._configStockAccount()
    #回测时需要用到当前的参数
    def _getStockMongoDbForBackTesting():
        data = copy.deepcopy(DyStockConfig.defaultMongoDb)

        # connection
        data['Connection']['Host'] = DyStockMongoDbEngine.host
        data['Connection']['Port'] = DyStockMongoDbEngine.port

        # Wind
        data["CommonDays"]["Wind"]['stockCommonDb'] = DyStockMongoDbEngine.stockCommonDb
        data["CommonDays"]["Wind"]['tradeDayTableName'] = DyStockMongoDbEngine.tradeDayTableName
        data["CommonDays"]["Wind"]['codeTableName'] = DyStockMongoDbEngine.codeTableName

        data["CommonDays"]["Wind"]['stockDaysDb'] = DyStockMongoDbEngine.stockDaysDb

        # TuShare
        data["CommonDays"]["TuShare"]['stockCommonDb'] = DyStockMongoDbEngine.stockCommonDbTuShare
        data["CommonDays"]["TuShare"]['tradeDayTableName'] = DyStockMongoDbEngine.tradeDayTableNameTuShare
        data["CommonDays"]["TuShare"]['codeTableName'] = DyStockMongoDbEngine.codeTableNameTuShare

        data["CommonDays"]["TuShare"]['stockDaysDb'] = DyStockMongoDbEngine.stockDaysDbTuShare

        # ticks
        data["Ticks"]["db"] = DyStockMongoDbEngine.stockTicksDb

        return data
    #
    def getConfigForBackTesting():
        """
            多进程回测需要当前进程的配置参数
        """
        data = {}
        data['exePath'] = DyCommon.exePath
        data['defaultHistDaysDataSource'] = DyStockCommon.defaultHistDaysDataSource
        data['tuSharePro'] = {'useTuSharePro': DyStockCommon.useTuSharePro,
                            'tuShareProToken': DyStockCommon.tuShareProToken,
                            }
        data['mongoDb'] = DyStockConfig._getStockMongoDbForBackTesting()

        return data
    #回测时设置配置
    def setConfigForBackTesting(data):
        DyCommon.exePath = data['exePath']
        DyStockCommon.defaultHistDaysDataSource = data['defaultHistDaysDataSource']
        DyStockCommon.useTuSharePro = data['tuSharePro']['useTuSharePro']
        DyStockCommon.tuShareProToken = data['tuSharePro']['tuShareProToken']

        DyStockConfig.configStockMongoDb(data['mongoDb'])
        