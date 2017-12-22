.. _archnotes:

*********************************
gipc's architecture in a nutshell
*********************************
- Child process creation and invocation is done via a thin wrapper around
  ``multiprocessing.Process``. On Unix-like systems, the inherited gevent hub as
  well as the inherited libev event loop become destroyed and re-initialized in
  the child before execution of the user-given target function.

- On Unix-like systems, gevent-cooperative child process monitoring is
  implemented with libev child watchers which rely on SIGCHLD signal
  transmission.

- gipc uses anonymous pipes as a stream-like transport layer for
  gevent-cooperative communication between greenlets within the same process or
  across process boundaries. By default, a binary ``pickle`` protocol is used
  which allows for transmitting arbitrary Python objects. Reading and writing on
  pipes is done with ``gevent``'s cooperative versions of ``os.read()`` and
  ``os.write()`` (on Unix-like systems they use non-blocking I/O, whereas on
  Windows a thread pool is used for emulating that behavior). On Linux, my test
  system (Xeon E5630) achieved a payload transfer rate of 1200 MB/s and a
  message transmission rate of 100.000 messages/s through one pipe between two
  processes.

- gipc automatically closes pipe handles in the parent process after being
  passed to the child, and also closes those in the child that were not
  explicitly transferred to it. This auto-close behavior might be a limitation
  in certain special cases. However, it automatically prevents file descriptor
  leakage and forces developers to make deliberate choices about which handles
  should be transferred explicitly.

- gipc provides convenience features such as a context manager for pipe
  handles or timeout controls based on ``gevent.Timeout``.

- Read/write operations on a pipe are ``gevent.lock.Semaphore``-protected
  and therefore greenthread-safe.
