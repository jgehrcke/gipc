# -*- coding: utf-8 -*-
#
#   Copyright (C) 2012 Jan-Philip Gehrcke
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
Example output for raw message transmission on Python 2.7.3
on Ubuntu 10.04 on a Xeon E5630 for
    N = 99999
    msg = "x"*21000+'\n'

2012-10-21 19:12:09,667 main# Read duration: 5.459 s
2012-10-21 19:12:09,668 main# Message transmission rate: 18319.271 msgs/s
2012-10-21 19:12:09,668 main# Data transfer rate: 366.900 MB/s

New binary protocol:
message size that optimizes data transfer rage:
2012-11-04 21:41:35,680 test_pipespeed# Read duration: 1.836 s
2012-11-04 21:41:35,680 test_pipespeed# Message transmission rate: 17851.744 msgs/s
2012-11-04 21:41:35,680 test_pipespeed# Data transfer rate: 1021.468 MB/s

Small messages:
2012-11-04 21:42:05,011 test_pipespeed# Read duration: 1.160 s
2012-11-04 21:42:05,011 test_pipespeed# Message transmission rate: 56520.141 msgs/s
2012-11-04 21:42:05,011 test_pipespeed# Data transfer rate: 0.054 MB/s
"""


import os
import sys
import logging
import time
from multiprocessing import Process, Condition
import gevent
import gpipe


logging.basicConfig(format='%(asctime)-15s %(funcName)s# %(message)s')
log = logging.getLogger()
log.setLevel(logging.DEBUG)
if sys.platform == 'win32':
    TIMER = time.clock
else:
    TIMER = time.time


MSG = 'A' * 9999


def main():
    # Init GPipe.

    # Spawn a greenlet that does something on the side.
    useless = gevent.spawn(do_something_useless_on_the_side)

    condition = Condition()
    elapsed = 0
    N = 1
    DELTA = 1

    while elapsed < DELTA:
        N *= 3
        reader, writer = gpipe.pipe()
        condition.acquire()
        p = gpipe.start_process(
            writer,
            writer_process,
            kwargs={'condition': condition, 'N': N})
        condition.wait()
        condition.release()
        result = None
        t = TIMER()
        while result != 'stop':
            result = reader.pickleget()
        elapsed = TIMER() - t
        p.join()
        #elapsed = 5

    mpertime = N/elapsed
    datasize_mb = float(len(MSG)*N)/1024/1024
    datarate_mb = datasize_mb/elapsed
    log.info("Read duration: %.3f s" % elapsed)
    log.info("Average message transmission rate: %.3f msgs/s" % mpertime)
    log.info("Data transfer rate: %.3f MB/s" % datarate_mb)
    useless.join()


def writer_process(writer, condition, N):
    condition.acquire()
    condition.notify()
    condition.release()
    for i in xrange(N):
        writer.pickleput(MSG)
    writer.pickleput('stop')


def do_something_useless_on_the_side():
    gevent.sleep(0.1)
    log.info("I'm doing nothing. PID %s" % os.getpid())
    gevent.sleep(0.1)
    log.info("Still nothing. PID %s" % os.getpid())


if __name__ == "__main__":
    main()

