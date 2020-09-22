import threading
import time
from datetime import datetime
from collections import namedtuple

# 自定义任务调度器
class DyScheduler:
    """
        任务调度器
        由于APScheduler可能会发生Job missed的情况，所以自己写一个。
        !!!不支持一天开始和结束的几分钟。
    """
    Job = namedtuple('Job', 'job dayOfWeek timeOfDay')
    precision = 60*2 # 2 minutes


    def __init__(self):
        self._jobs = []# nametuple实例集合

        self._active = False
        self._hand = None
        self._preTime = None
    # Job是函数指针
    def addJob(self, job, dayOfWeek, timeOfDay):
        """
            @job: job的处理函数
            @dayOfWeek: set, like {1, 2, 3, 4, 5, 6, 7}
            @timeOfDay: string, like '18:31:00'
        """
        self._jobs.append(self.Job(job, dayOfWeek, timeOfDay))# 生成一个NameTUple实例
    # 真正线程执行的是这个函数，循环执行
    def _run(self):
        while self._active:# 开启
            now = datetime.now()
            dayOfWeek = now.weekday() + 1
            curTime = now.strftime('%H:%M:%S')

            if self._preTime is not None:# 刚开始为空
                for job in self._jobs:# 执行条件，过了8.30执行一次，因为再过不满足条件，且周一到周五，另外一个时间是15：45，
                    if dayOfWeek in job.dayOfWeek and self._preTime <= job.timeOfDay < curTime:
                        job.job()# 执行具体函数，_beginday or _endday

            self._preTime = curTime# 在这里初始化

            time.sleep(self.precision)# 睡眠两分钟
    # 从这里开始任务调度器
    def start(self):
        self._active = True

        self._hand = threading.Thread(target=self._run)# 又是开始了一个线程
        self._hand.start()
    # 关闭
    def shutdown(self):
        self._active = False
        # 等待关闭成功
        self._hand.join()

        self._hand = None# 重置
        self._preTime = None