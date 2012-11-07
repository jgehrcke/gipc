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

Small messages:
2012-11-06 19:46:19,591 main#  Overall benchmark result:
2012-11-06 19:46:19,591 main#  N: 262144
2012-11-06 19:46:19,591 main#  Read duration: 1.715+/-0.005 s
2012-11-06 19:46:19,591 main#  Average msg tx rate: 152839.956+/-453.931 msgs/s
2012-11-06 19:46:19,592 main#  Payload transfer rate: 0.146+/-0.000 MB/s

Large messages:
2012-11-06 19:45:39,984 main#  Overall benchmark result:
2012-11-06 19:45:39,984 main#  N: 32768
2012-11-06 19:45:39,984 main#  Read duration: 1.378+/-0.020 s
2012-11-06 19:45:39,984 main#  Average msg tx rate: 23783.522+/-342.499 msgs/s
2012-11-06 19:45:39,985 main#  Payload transfer rate: 1360.881+/-19.598 MB/s
"""


import os
import sys
import logging
import time
from multiprocessing import Process, Condition
import gevent
import gevent.hub
import gpipe
import numpy
import math

logging.basicConfig(format='%(asctime)-15s %(funcName)s# %(message)s')
log = logging.getLogger()
log.setLevel(logging.INFO)
if sys.platform == 'win32':
    TIMER = time.clock
else:
    TIMER = time.time


MSG = 'A' * 199999
REPETITIONS = 3


def main():
    elapsed = 0
    N = 1

    log.info("Determining N ...")

    # Find N with which benchmark lasts between 1 and two seconds
    while elapsed < 1:
        N *= 2
        N, elapsed = benchmark(N)

    log.info("N = %s" % N)
    log.info("Running %s benchmarks ..." % REPETITIONS)
    elapsed_values = []
    # Repeat benchmark with last N value, collect data
    for _ in xrange(REPETITIONS):
        N, elapsed = benchmark(N)
        elapsed_values.append(elapsed)
        # Evaluate
        mpertime = N/elapsed
        datasize_mb = float(len(MSG)*N)/1024/1024
        datarate_mb = datasize_mb/elapsed
        log.info(" Single benchmark result:")
        log.info("  --> N: %s, MSG length: %s" % (N, len(MSG)))
        log.info("  --> Read duration: %.3f s" % elapsed)
        log.info("  --> Average msg tx rate: %.3f msgs/s" % mpertime)
        log.info("  --> Payload transfer rate: %.3f MB/s" % datarate_mb)

    e_mean = numpy.mean(elapsed_values)
    e_err = numpy.std(elapsed_values)/math.sqrt(len(elapsed_values)-1)
    e_rel_err = e_err/e_mean
    datarate_mb_mean = datasize_mb/e_mean
    datarate_mb_err = datarate_mb_mean * e_rel_err
    mpertime_mean = N/e_mean
    mpertime_err = mpertime_mean * e_rel_err
    log.info(" Overall benchmark result:")
    log.info(" N: %s" % N)
    log.info(" Read duration: %.3f+/-%.3f s" % (e_mean, e_err))
    log.info(" Average msg tx rate: %.3f+/-%.3f msgs/s" %
        (mpertime_mean, mpertime_err))
    log.info(" Payload transfer rate: %.3f+/-%.3f MB/s" %
        (datarate_mb_mean, datarate_mb_err))


def benchmark(N):
    condition = Condition()
    result = None
    reader, writer = gpipe.pipe()
    condition.acquire()
    p = gpipe.start_process(
        writer,
        writer_process,
        kwargs={'condition': condition, 'N': N})
    condition.wait()
    condition.release()
    t = TIMER()
    while result != 'stop':
        result = reader.get()
    elapsed = TIMER() - t
    p.join()
    return N, elapsed


def writer_process(writer, condition, N):
    condition.acquire()
    condition.notify()
    condition.release()
    for i in xrange(N):
        writer.put(MSG)
    writer.put('stop')


if __name__ == "__main__":
    main()

