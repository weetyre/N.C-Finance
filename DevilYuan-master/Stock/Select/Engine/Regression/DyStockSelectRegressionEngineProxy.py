import multiprocessing
import threading

from .DyStockSelectRegressionEngineProcess import *
from ....Common.DyStockCommon import DyStockCommon

# 选股回归进程
class DyStockSelectRegressionEngineProxy(threading.Thread):
    threadMode = False # only for debug without care about errors


    def __init__(self, eventEngine):
        super().__init__()

        self._eventEngine = eventEngine

        self._ctx = multiprocessing.get_context('spawn')# 调用多进程
        self._queue = self._ctx.Queue() # queue to receive event from child processes

        self._processes = []
        self._childQueues = []

        self.start()
    # 紧接着执行run函数
    def run(self):
        while True:
            event = self._queue.get()# 如果队列为空等待，且这个queue为出队列

            self._eventEngine.put(event)# 分发给引擎执行
    # 要调用这个
    def startRegression(self, tradeDays, strategy, codes = None):
        """
            @strategy: {'class':strategyCls, 'param': strategy paramters}
        """
        _childQueue = self._ctx.Queue()# 返回一个入队列，为了进一步功能添加的
        self._childQueues.append(_childQueue)#

        if self.threadMode:# 如果是线程模式
            p = threading.Thread(target=dyStockSelectRegressionEngineProcess, args=(self._queue, _childQueue, tradeDays, strategy, codes, DyStockCommon.defaultHistDaysDataSource))
        else:
            p = self._ctx.Process(target=dyStockSelectRegressionEngineProcess, args=(self._queue, _childQueue, tradeDays, strategy, codes, DyStockCommon.defaultHistDaysDataSource))

        p.start()# 用进程执行那个函数

        self._processes.append(p)# 添加现有进程
