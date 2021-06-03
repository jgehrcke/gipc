# -*- coding: utf-8 -*-
# Copyright 2012-2021 Dr. Jan-Philip Gehrcke. See LICENSE file for details.

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

import hashlib
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


WINDOWS = False
if sys.platform == 'win32':
    WINDOWS = True


timer = time.time
if hasattr(time, 'perf_counter'):
    timer = time.perf_counter


def main():

    log.info('Creating data ...')

    N = 10**7
    n = 80

    if platform.python_implementation() == 'PyPy':
        # This example seems to suffer from a severe performance problem on
        # PyPy. On my machine I got 890 MBytes/s on CPython 3.6.3 / gevent
        # 1.3.6, whereas with PyPy35-6.0.0 (everything else constant) I saw 3
        # MB/s. Adopt to this so that this executes within reasonable time
        # during CI.
        N = 10**6
        n = 20

    if platform.python_implementation() == 'CPython' and WINDOWS:
        # Temporarily work around the inability to send large messages on
        # Windows. Fixing that is tracked here:
        # https://github.com/jgehrcke/gipc/issues/69
        N = 10**6
        n = 20

    # Concatenate a smaller chunk of random data multiple times (that's faster
    # than creating a big chunk of random data).
    data = os.urandom(N) * n
    mbytes = len(data) / 1024.0 / 1024
    log.info('Data size: %s MBytes' % mbytes)
    checksum = hashlib.md5(data).digest()

    with gipc.pipe(duplex=True) as (c, p):
        log.info('Test with default pipe...')
        spawn_child_transfer(c, p, data, checksum)

    with gipc.pipe(duplex=True, encoder=None, decoder=None) as (c, p):
        log.info('Test with raw pipe...')
        spawn_child_transfer(c, p, data, checksum)


def spawn_child_transfer(childhandler, parenthandler, data, checksum):

    p = gipc.start_process(target=child, args=(childhandler, checksum))

    assert parenthandler.get() == b'start'
    log.info('Sending data')
    t0 = timer()

    parenthandler.put(data)
    assert parenthandler.get() == b'done'
    delta = timer() - t0

    log.info('Child confirmed that it received data, checksum matches')
    p.join()
    assert p.exitcode == 0

    log.info('Duration: %.3f s' % delta)
    mbytes = len(data) / 1024.0 / 1024

    if delta < 10 ** -7:
        log.info('Clock resolution too small to calculate meaningful rate')
    else:
        rate = mbytes / delta
        log.info('Rate: %.2f MBytes/s' % rate)


def child(childhandler, reference_checksum):
    childhandler.put(b'start')
    data = childhandler.get()
    childhandler.put(b'done')
    checksum = hashlib.md5(data).digest()
    assert checksum == reference_checksum


if __name__ == "__main__":
    main()
