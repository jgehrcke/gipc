import gevent
import gipc
import time
import sys
WINDOWS = sys.platform == "win32"
if WINDOWS:
    timer = time.clock
else:
    timer = time.time


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
        print "Time delta: %.8f s." % abs(ptime - ctime)


def writer_process(cend):
    with cend:
        assert cend.get() == "SYN"
        cend.put("ACK")
        # Now in sync with parent.
        cend.put(timer())


if __name__ == "__main__":
    main()
