# -*- coding: utf-8 -*-
# Copyright 2012-2017 Jan-Philip Gehrcke. See LICENSE file for details.


import gevent
import gipc
import platform

print("Platform: %s" % (platform.platform(), ))
print("gevent version: %s" % (gevent.__version__, ))
print("Python version: %s %s" % (
    platform.python_implementation(), platform.python_version(), )
)


def main():
    with gipc.pipe() as (r, w):
        p = gipc.start_process(target=child_process, args=(r, ))
        wg = gevent.spawn(writegreenlet, w)
        try:
            p.join()
        except KeyboardInterrupt:
            # `kill()` always returns None and never raises an exception.
            wg.kill(block=True)
            print('Send SIGTERM to child process')
            p.terminate()

    # Wait for child to terminate, expect some more SIGINTs but ignore them.
    # Note: there are still time windows when SIGINT is not handled by us but by
    # the interpreter but when assumung that a human sends them via keyboard
    # input this is fine.
    while p.exitcode is None:
        try:
            p.join()
        except KeyboardInterrupt:
            pass
    print('Child process terminated. Exit code: %s' % (p.exitcode, ))


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
    def inthandler(_, __):
        print('Ignored SIGINT in child')

    import signal
    signal.signal(signal.SIGINT, inthandler)

    while True:
        print("Child process got message through pipe:\n\t'%s'" % reader.get())


if __name__ == "__main__":
    main()
