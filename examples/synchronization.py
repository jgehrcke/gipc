# -*- coding: utf-8 -*-
# Copyright 2012-2021 Dr. Jan-Philip Gehrcke. See LICENSE file for details.


import gevent
import gipc
import time


timer = time.time
# We are about to measure a really small time difference. On Windows, when using
# `time.time()`, the difference will always be measured as 0 because the small
# time resolution (just about ~16 ms) if this type of clock. `time.clock()` has
# a much higher precison on Windows than `time.time()` but it cannot be used to
# measure a time difference across two processes. `perf_counter` is new since
# Python 3.3 and should do the job for all platforms. It is documented with "It
# does include time elapsed during sleep and is system-wide".
if hasattr(time, 'perf_counter'):
    timer = time.perf_counter


def main():
    with gipc.pipe(duplex=True) as (cend, pend):
        # `cend` is the channel end for the child, `pend` for the parent.
        p = gipc.start_process(writer_process, args=(cend,))
        # Synchronize with child process.
        pend.put("SYN")
        assert pend.get() == "ACK"
        # Now in sync with child.
        ptime = timer()
        ctime = pend.get()
        p.join()
        print("Time delta: %.8f s." % abs(ptime - ctime))


def writer_process(cend):
    with cend:
        assert cend.get() == "SYN"
        cend.put("ACK")
        # Now in sync with parent.
        cend.put(timer())


if __name__ == "__main__":
    main()

