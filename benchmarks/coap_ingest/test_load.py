# TODO: Start the device server on remote server/ raspberry pi (Use paramiko?)
#  TODO: Start the perf_stat_generator on remote server/ raspberry pi (Use paramiko?)
# generate load (configurable) & wait for cool-off period for some sec
import load_generator
import time
from foglamp import logger
_load_lst = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
_mixed_load = True
_wait_time_between_load = 2
_logger = logger.setup(logger_name=__name__, destination=logger.PERFLOG, level=logger.level_info)

for _load in _load_lst:
    _actual_load = _load*9 if _mixed_load else _load
    _logger.info("Load: {}".format(_actual_load))
    #print("Load: {}".format(_actual_load))
    load_generator.main(job=_load, message_type=_mixed_load)
    time.sleep(_wait_time_between_load)
    _wait_time_between_load += 1


# TODO: Stop the perf_stat_generator on remote server/ raspberry pi (Use paramiko?)
# TODO: Stop the device server
# TODO: Generate report
#import stats_collector


