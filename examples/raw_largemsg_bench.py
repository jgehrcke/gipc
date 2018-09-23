# -*- coding: utf-8 -*-
# Copyright 2012-2017 Jan-Philip Gehrcke. See LICENSE file for details.

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
import platform

sys.path.insert(0, os.path.abspath('..'))
import gipc

log = logging.getLogger()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
    datefmt="%y%m%d-%H:%M:%S"
    )

N = 10**7
n = 80

if platform.python_implementation() == 'PyPy':
    # This example seems to suffer from a severe performance problem on PyPy. On
    # my machine I got 890 MBytes/s on CPython 3.6.3 / gevent 1.3.6, whereas
    # with PyPy35-6.0.0 (everything else constant) I saw 3 MB/s. Adopt to this
    # so that this executes within reasonable time during CI.
    N = 10**6
    n = 20

log.info('Creating data ...')
DATA = os.urandom(N) * n
mbytes = N * n / 1024.0 / 1024
log.info('MBytes: %s' % mbytes)


def spawn_child_transfer(childhandler, parenthandler):

    p = gipc.start_process(target=child, args=(childhandler,))

    assert parenthandler.get() == b'start'

    log.info('Sending data')
    t0 = time.time()
    parenthandler.put(DATA)
    assert parenthandler.get() == b'done'
    delta = time.time() - t0

    log.info('Child confirmed that it received data')

    p.join()
    assert p.exitcode == 0
    log.info('Duration: %.3f s' % delta)
    rate = mbytes/delta
    log.info('Rate: %.2f MBytes/s' % rate)


def child(childhandler):
    childhandler.put(b'start')
    d = childhandler.get()
    childhandler.put(b'done')
    # `DATA` is available only on POSIX-compliant systems (after fork()).
    assert DATA == d


with gipc.pipe(duplex=True, encoder=None, decoder=None) as (c, p):
    log.info('Test with raw pipe...')
    spawn_child_transfer(c, p)


with gipc.pipe(duplex=True) as (c, p):
    log.info('Test with default pipe...')
    spawn_child_transfer(c, p)
