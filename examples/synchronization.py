import time
import gevent
import gipc


def main():
    with gipc.pipe() as (r1, w1):
        with gipc.pipe() as (r2, w2):
            p = gipc.start_process(
                writer_process,
                kwargs={'writer': w2, 'syncreader': r1}
                )
            result = None
            # Synchronize with child process.
            w1.put("SYN")
            assert r2.get() == "ACK"
            t = time.time()
            while result != "STOP":
                result = r2.get()
            elapsed = time.time() - t
            p.join()
            print "Time elapsed: %.3f s" % elapsed


def writer_process(writer, syncreader):
    with writer:
        assert syncreader.get() == "SYN"
        writer.put("ACK")
        for i in xrange(1000):
            writer.put("A"*1000)
        writer.put('STOP')


if __name__ == "__main__":
    main()
