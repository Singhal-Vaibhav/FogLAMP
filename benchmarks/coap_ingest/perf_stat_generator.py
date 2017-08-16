import psutil
import os
import threading
import time
from foglamp import logger


class PeriodicStatsReporter(threading.Thread):
    def __init__(self, interval, func, *args, **kwargs):
        threading.Thread.__init__(self)
        self.interval = interval  # seconds between calls
        self.func = func          # function to call
        self.args = args          # optional positional argument(s) for call
        self.kwargs = kwargs      # optional keyword argument(s) for call
        self.runable = True

    def run(self):
        while self.runable:
            self.func(*self.args, **self.kwargs)
            time.sleep(self.interval)

    def stop(self):
        self.runable = False


def get_process_id(process_name=None):
    # TODO : Handle Cases when we get multiple id's for same process name
    #pids = []
    _pid = ''
    for line in os.popen("ps ax | grep " + process_name + " | grep -v grep"):
        fields = line.split()
        _pid = fields[0]
        #pids.append(pid)
    return _pid


def report_stats(p):
    #print('Process ID:{}'.format(_pid))
    _logger = logger.setup(logger_name=__name__, destination=logger.PERFLOG, level=logger.level_info)
    _logger.info("PID: {}, CPUPct: {}, MemoryPct: {}".format(p.pid, p.cpu_percent(), p.memory_percent()))
    #print("Time: {}, PID: {}, CPUPct: {}, MemoryPct: {}".format(datetime.now(), p.pid, p.cpu_percent(), p.memory_percent()))


def main():
    PROCNAME = "foglamp.device"
    _pid = int(get_process_id(PROCNAME))
    p = psutil.Process(_pid)
    print('Process ID:{}'.format(_pid))
    thread = PeriodicStatsReporter(3, report_stats, p)
    print("starting")
    thread.start()
    thread.join()  # allow thread to execute a while...
    thread.stop()
    print('stopped')

# TODO : No main, start/stop should be controlled by an external script
main()
