# -*- coding: utf-8 -*-
# Copyright 2012-2021 Dr. Jan-Philip Gehrcke. See LICENSE file for details.


"""
This example contains quite a bit of commentary and code around signal handling.
The purpose of signal handling in this program is to provide a clean program
shutdown mechanism which can be triggered with SIGINT, and to support multiple
SIGINTs to arrive where only the first one should invoke the shutdown (and
subsequent ones should be ignored). Notably, doing so reliably and correctly is
only possible with custom signal handlers. Working with CPython's default SIGINT
handler (which raises the `KeyboardInterrupt` exception) and trying to scatter
`try ... except KeyboardInterrupt:` exception handlers across is very hard to
get right (race condition free) as of the complex code exectuion flow in this
program.
"""


import gevent
import gipc
import platform
import signal


print("Platform: %s" % (platform.platform(), ))
print("gevent version: %s" % (gevent.__version__, ))
print("Python version: %s %s" % (
    platform.python_implementation(), platform.python_version(), )
)


# Control variable. Will be updated from within signal handler.
shutdown = False


def initiate_shutdown(_, __):
    """
    I think three aspects are noteworthy of this function:

    1) When the handler for a particular signal is invoked, that signal is
       automatically blocked until the handler returns. That means that if two
       signals of the same kind, SIGINT in this case, arrive close together, the
       second one will be held until the first has been handled.

    2) The set of actions that can safely be performed within a signal handler
       is small. On Linux it is safe to call `signal()` (see
       http://man7.org/linux/man-pages/man7/signal-safety.7.html) to install a
       different signal handler but notably as of the CERT C Coding Standard,
       rule SIG30-C, `signal()` is one of the only four C standard library
       functions which can safely be called from within a signal handler.

    3) For educational purposes it would be good to `print()` here (as I have
       done in the rest of the program) so that the control flow is obvious from
       the program output. However, then the program sould not be correct
       anymore: Python's IO system is not reentrant
       (https://bugs.python.org/issue24283).
    """
    # Let the program know that it should initiate the shutdown procedure.
    global shutdown
    shutdown = True

    # Ignore subsequent SIGINTs.
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def main():

    # Make the first SIGINT received by this program initiate the shutdown
    # procedure.
    signal.signal(signal.SIGINT, initiate_shutdown)

    def _writegreenlet(writer):
        while True:
            writer.put('Msg sent from a greenlet running in the main process!')
            gevent.sleep(1)

    # Create gipc pipe and expose the read end as `r` and the write end as `w`.
    with gipc.pipe() as (r, w):

        # Start child process for receiving messages. It inherits the standard
        # streams of this process and prints the received messages to stdout.
        p = gipc.start_process(target=child_process, args=(r, ))

        # Start greenlet (in the current, the parent, process). It periodically
        # sends a message to the child process through the pipe, via gipc's IPC.
        g = gevent.spawn(_writegreenlet, w)

        # Keep the pipe alive, and let the two entities communicate as long as
        # the shutdown procedure has not been invoked.
        while not shutdown:
            gevent.sleep(0.01)

        # Once we're here the shutdown procedure has been invoked. Terminate the
        # message sender greenlet. `kill()` always returns None; never raises an
        # exception.
        g.kill(block=True)

        print('Write greenlet terminated. Send SIGTERM to child process')
        p.terminate()

        # Wait for child process to terminate, reap it (read exit code).
        p.join()
        print('Child process terminated. Exit code: %s' % (p.exitcode, ))


def child_process(reader):
    """
    Ignore SIGINT (default handler in CPython is to raise KeyboardInterrupt,
    which is undesired here). The parent handles it, and instructs the child to
    clean up as part of handling it.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while True:
        print("Child process got message through pipe:\n\t'%s'" % reader.get())


if __name__ == "__main__":
    main()
