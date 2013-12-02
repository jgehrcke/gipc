# -*- coding: utf-8 -*-
# Copyright 2012-2013 Jan-Philip Gehrcke. See LICENSE file for details.

"""
Example output (Ubuntu 12.04, Python 2.7.3, Xeon E5-2650)

$ python raw_largemsg_bench.py
20:37:22,617.0  [5528] Creating data...
20:37:23,984.0  [5528] Mbytes: 762.939453125
20:37:23,985.5  [5528] Test with raw pipe...
20:37:23,998.5  [5528] Sending data.
20:37:26,247.3  [5528] Data received, verifying...
20:37:27,24.9   [5528] Duration: 2.248 s
20:37:27,25.1   [5528] Rate: 339.31 MBytes/s
20:37:27,25.7   [5528] Test with default pipe...
20:37:27,45.1   [5528] Sending data.
20:37:31,414.5  [5528] Data received, verifying...
20:37:32,193.2  [5528] Duration: 4.369 s
20:37:32,193.4  [5528] Rate: 174.62 MBytes/s
"""

import os
import sys
import time
import logging

sys.path.insert(0, os.path.abspath('..'))
import gipc

logging.basicConfig(
    format='%(asctime)s,%(msecs)-6.1f [%(process)d] %(message)s',
    datefmt='%H:%M:%S')
log = logging.getLogger()
log = logging.getLogger()
log.setLevel(logging.INFO)


N = 10**7
n = 80
log.info("Creating data...")
DATA = os.urandom(N)*n
mbytes = n*N / 1024.0 / 1024
log.info("Mbytes: %s" % mbytes)


def spawn_child_transfer(childhandler, parenthandler):
    p = gipc.start_process(target=child, args=(childhandler,))
    assert parenthandler.get() == "start"
    log.info("Sending data.")
    t0 = time.time()
    parenthandler.put(DATA)
    assert parenthandler.get() == "done"
    delta = time.time() - t0
    log.info("Data received, verifying...")
    p.join()
    assert p.exitcode == 0
    log.info("Duration: %.3f s" % delta)
    rate = mbytes/delta
    log.info("Rate: %.2f MBytes/s" % rate)


def child(childhandler):
    childhandler.put("start")
    d = childhandler.get()
    childhandler.put("done")
    # `DATA` is available only on POSIX-compliant systems (after fork()).
    assert DATA == d


with gipc.pipe(duplex=True, encoder=None, decoder=None) as (c, p):
    log.info("Test with raw pipe...")
    spawn_child_transfer(c, p)


with gipc.pipe(duplex=True) as (c, p):
    log.info("Test with default pipe...")
    spawn_child_transfer(c, p)