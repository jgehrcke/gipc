# -*- coding: utf-8 -*-
# Copyright 2012-2017 Jan-Philip Gehrcke. See LICENSE file for details.


import gevent
import gipc


def main():
    with gipc.pipe() as (r, w):
        p = gipc.start_process(target=child_process, args=(r, ))
        wg = gevent.spawn(writegreenlet, w)
        try:
            p.join()
        except KeyboardInterrupt:
            # `kill()` always returns None and never raises an exception.
            wg.kill(block=True)
            p.terminate()
        p.join()


def writegreenlet(writer):
    while True:
        writer.put('I was sent from a greenlet running in the main process!')
        gevent.sleep(1)


def child_process(reader):
    """
    Ignore SIGINT (default handler in CPython is to raise KeyboardInterrupt,
    which is undesired here). The parent handles it, and instructs the child to
    clean up as part of handling it.
    """
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while True:
        print("Child process got message through pipe:\n\t'%s'" % reader.get())


if __name__ == "__main__":
    main()
