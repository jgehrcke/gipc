# -*- coding: utf-8 -*-
# Copyright 2012-2021 Dr. Jan-Philip Gehrcke. See LICENSE file for details.


"""
Example output for Python 2.7.3 on Ubuntu 10.04 on a Xeon E5630 for

# MSG length optimized for throughput (length 64000):
14:52:07,606.2  [26430]benchmark_manager#  Overall benchmark result:
14:52:07,606.3  [26430]benchmark_manager#  N: 32768
14:52:07,606.4  [26430]benchmark_manager#  Read duration: 1.662+/-0.005 s
14:52:07,606.4  [26430]benchmark_manager#  Average msg tx rate: 19711.600+/-65.113 msgs/s
14:52:07,606.5  [26430]benchmark_manager#  Payload transfer rate: 1203.101+/-3.974 MB/s

# Small messages (length 1):
14:52:14,283.6  [26430]benchmark_manager#  Overall benchmark result:
14:52:14,283.7  [26430]benchmark_manager#  N: 131072
14:52:14,283.7  [26430]benchmark_manager#  Read duration: 1.323+/-0.001 s
14:52:14,283.8  [26430]benchmark_manager#  Average msg tx rate: 99096.931+/-73.556 msgs/s
14:52:14,283.9  [26430]benchmark_manager#  Payload transfer rate: 0.095+/-0.000 MB/s
"""


import os
import sys
import logging
import time
import math

import gevent
sys.path.insert(0, os.path.abspath('..'))
import gipc

logging.basicConfig(
    format='%(asctime)s,%(msecs)-6.1f [%(process)d]%(funcName)s# %(message)s',
    datefmt='%H:%M:%S')
log = logging.getLogger()
log = logging.getLogger()
log.setLevel(logging.INFO)


timer = time.time
if hasattr(time, 'perf_counter'):
    timer = time.perf_counter


if sys.version_info[0] == 3:
    xrange = range


def main():
    repetitions = 3

    msg = 'A' * 64000
    log.info("Throughput benchmark")
    log.info("Determining N ...")
    benchmark_manager(msg, repetitions)

    msg = "a"
    log.info("Transmission benchmark")
    log.info("Determining N ...")
    benchmark_manager(msg, repetitions)


def benchmark_manager(msg, repetitions):
    elapsed = 0
    N = 1
    # Find N so that benchmark lasts between 1 and two seconds
    while elapsed < 1:
        N *= 2
        N, elapsed = benchmark(N, msg)

    log.info("N = %s" % N)
    log.info("Running %s benchmarks ..." % repetitions)
    elapsed_values = []
    # Repeat benchmark, save statistics
    for _ in xrange(repetitions):
        N, elapsed = benchmark(N, msg)
        elapsed_values.append(elapsed)
        # Evaluate stats of single run
        mpertime = N/elapsed
        datasize_mb = float(len(msg)*N)/1024/1024
        datarate_mb = datasize_mb/elapsed
        log.info(" Single benchmark result:")
        log.info("  --> N: %s, MSG length: %s" % (N, len(msg)))
        log.info("  --> Read duration: %.3f s" % elapsed)
        log.info("  --> Average msg tx rate: %.3f msgs/s" % mpertime)
        log.info("  --> Payload transfer rate: %.3f MB/s" % datarate_mb)

    # Evaluate stats of all runs
    e_mean = mean(elapsed_values)
    e_err = pstdev(elapsed_values)/math.sqrt(len(elapsed_values)-1)
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


def benchmark(N, msg):
    result = None
    with gipc.pipe() as (syncr, syncw):
        with gipc.pipe() as (reader, writer):
            p = gipc.start_process(
                writer_process,
                kwargs={
                    'writer': writer,
                    'syncr': syncr,
                    'N': N,
                    'msg': msg})
             # Synchronize with child process
            syncw.put("SYN")
            assert reader.get() == "ACK"
            t = timer()
            while result != 'stop':
                result = reader.get()
            elapsed = timer() - t
            p.join()
    return N, elapsed


def writer_process(writer, syncr, N, msg):
    with writer:
        assert syncr.get() == "SYN"
        writer.put("ACK")
        for i in xrange(N):
            writer.put(msg)
        writer.put('stop')


# Credit: http://stackoverflow.com/a/27758326/145400
def mean(data):
    """Return the sample arithmetic mean of data."""
    n = len(data)
    if n < 1:
        raise ValueError('mean requires at least one data point')
    return sum(data)/float(n)

def _ss(data):
    """Return sum of square deviations of sequence data."""
    c = mean(data)
    ss = sum((x-c)**2 for x in data)
    return ss

def pstdev(data):
    """Calculates the population standard deviation."""
    n = len(data)
    if n < 2:
        raise ValueError('variance requires at least two data points')
    ss = _ss(data)
    pvar = ss/n # the population variance
    return pvar**0.5


if __name__ == "__main__":
    main()

