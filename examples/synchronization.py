import time
import gevent
import gipc


def main():
    with gipc.pipe(duplex=True) as (cend, pend):
        # `cend` is the channel end for the child, `pend` for the parent.
        p = gipc.start_process(writer_process, args=(cend,))
        # Synchronize with child process.
        pend.put("SYN")
        assert pend.get() == "ACK"
        # Now in sync with child.
        t = time.time()
        while pend.get() != "STOP":
            pass
        elapsed = time.time() - t
        p.join()
        print "Time elapsed: %.3f s" % elapsed


def writer_process(cend):
    with cend:
        assert cend.get() == "SYN"
        cend.put("ACK")
        # Now in sync with parent.
        for i in xrange(1000):
            cend.put("A"*1000)
        cend.put("STOP")


if __name__ == "__main__":
    main()
