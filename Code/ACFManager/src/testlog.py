import time
import random
import logging
from acris import MpLogger
import os
import multiprocessing as mp

def subproc(limit=1, logger_info=None):
    logger = MpLogger.get_logger(logger_info, name="acrilog.subproc", )
    for i in range(limit):
        sleep_time = 3/random.randint(1,10)
        time.sleep(sleep_time)
        logger.info("proc [%s]: %s/%s - sleep %4.4ssec" % (os.getpid(), i, limit, sleep_time))

level_formats = {logging.DEBUG:"[ %(asctime)s ][ %(levelname)s ][ %(message)s ][ %(module)s.%(funcName)s(%(lineno)d) ]",
                'default':   "[ %(asctime)s ][ %(levelname)s ][ %(message)s ]",
                }

mplogger = MpLogger(logging_level=logging.DEBUG, level_formats=level_formats, datefmt='%Y-%m-%d,%H:%M:%S.%f')
mplogger.start(name='main_process')
logger = MpLogger.get_logger(mplogger.logger_info())

logger.debug("starting sub processes")
procs = list()
for limit in [1, 1]:
    proc = mp.Process(target=subproc, args=(limit, mplogger.logger_info(),))
    procs.append(proc)
    proc.start()

for proc in procs:
    if proc:
        proc.join()

logger.debug("sub processes completed")

mplogger.stop()