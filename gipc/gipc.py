# -*- coding: utf-8 -*-
# Copyright 2012-2013 Jan-Philip Gehrcke. See LICENSE file for details.


"""
gipc: child processes and IPC for gevent.

With gipc (pronunciation “gipsy”), malicious side-effects of child process
creation in the context of gevent are prevented. The API of
multiprocessing.Process objects is provided in a gevent-cooperative fashion.
Furthermore, gipc comes up with a pipe-based transport layer for
gevent-cooperative inter-process communication.
"""


import os
import io
import sys
import struct
import logging
import multiprocessing
import multiprocessing.forking
import multiprocessing.process
from itertools import chain
try:
    import cPickle as pickle
except ImportError:
    import pickle
WINDOWS = sys.platform == "win32"
if WINDOWS:
    import msvcrt
import gevent
import gevent.os
import gevent.lock
import gevent.event


# Logging for debugging purposes.
# Note: naive usage of logging from within multiple processes might yield mixed
# messages.
log = logging.getLogger("gipc")


class GIPCError(Exception):
    """Is raised upon general errors. All other exception types derive from
    this one.
    """
    pass


class GIPCClosed(GIPCError):
    """Is raised upon operation on closed handle.
    """
    pass


class GIPCLocked(GIPCError):
    """Is raised upon attempt to close a handle which is currently locked for
    I/O.
    """
    pass


def _newpipe():
    """Create new `os.pipe()` and return `(_GIPCReader, _GIPCWriter)` tuple.

    os.pipe() implementation on Windows (http://bit.ly/RDuKUm):
       - CreatePipe(&read, &write, NULL, 0)
       - anonymous pipe, system handles buffer size
       - anonymous pipes are implemented using named pipes with unique names
       - asynchronous (overlapped) read and write operations not supported
     os.pipe() implementation on Unix (http://linux.die.net/man/7/pipe):
       - based on pipe()
       - common Linux: pipe buffer is 4096 bytes, pipe capacity is 65536 bytes
    """
    r, w = os.pipe()
    return (_GIPCReader(r), _GIPCWriter(w))


def pipe(duplex=False):
    """Create a pipe-based message transport channel and return corresponding
    handles for reading and writing data.

    Allows for gevent-cooperative transmission of pickleable objects. Data can
    be sent between greenlets within one process or across processes (created
    via :func:`start_process`).

    :arg duplex:
        - If ``False`` (default), create a unidirectional pipe-based message
          transport channel and return the corresponding
          ``(_GIPCReader, _GIPCWriter)`` handle pair.
        - If ``True``, create a bidirectional message transport channel based
          on two pipes and return the corresponding
          ``(_GIPCDuplexHandle, _GIPCDuplexHandle)`` handle pair.

    :returns:
        - ``duplex=False``: ``(reader, writer)`` 2-tuple. The first element is
          of type :class:`gipc._GIPCReader`, the second of type
          :class:`gipc._GIPCWriter`. Both inherit from
          :class:`gipc._GIPCHandle`.
        - ``duplex=True``: ``(handle, handle)`` 2-tuple. Both elements are of
          type :class:`gipc._GIPCDuplexHandle`.


    :class:`gipc._GIPCHandle` and :class:`gipc._GIPCDuplexHandle`  instances
    are recommended to be used with Python's context manager as indicated in
    the following examples::

        with pipe() as (r, w):
            do_something(r, w)

    ::

        reader, writer = pipe()

        with reader:
            do_something(reader)
            with writer as w:
                do_something(w)

    ::

        with pipe(duplex=True) as (h1, h2):
            h1.put(1)
            assert h2.get() == 1
            h2.put(2)
            assert h1.get() == 2


    The transport layer is based on ``os.pipe()`` (i.e.
    `CreatePipe() <http://msdn.microsoft.com/en-us/library/windows/desktop/aa365152%28v=vs.85%29.aspx>`_
    on Windows and `pipe() <http://www.kernel.org/doc/man-pages/online/pages/man2/pipe.2.html>`_
    on POSIX-compliant systems).
    """
    pair1 = _newpipe()
    if not duplex:
        return _PairContext(pair1)
    pair2 = _newpipe()
    return _PairContext((
        _GIPCDuplexHandle((pair1[0], pair2[1])),
        _GIPCDuplexHandle((pair2[0], pair1[1]))))


def start_process(target, args=(), kwargs={}, daemon=None, name=None):
    """Start child process and execute function ``target(*args, **kwargs)``.
    Any existing instance of :class:`gipc._GIPCHandle` or
    :class:`gipc._GIPCDuplexHandle` can be passed to the child process via
    ``args`` and/or ``kwargs``.

    .. note::

        Compared to the canonical `multiprocessing.Process()` constructor, this
        function

        - returns a :class:`gipc._GProcess` instance which is compatible with
          the `multiprocessing.Process` API.
        - also takes the essential ``target``, ``arg=()``, and ``kwargs={}``
          arguments.
        - introduces the ``daemon=None`` argument.
        - does not accept the ``group`` argument (being an artifact from
          ``multiprocessing``'s compatibility with ``threading``).
        - starts the process, i.e. a subsequent call to the ``start()`` method
          of the returned object is redundant.

    :arg target:
        Function to be called in child as ``target(*args, **kwargs)``.

    :arg args:
        Tuple defining positional arguments provided to ``target``.

    :arg kwargs:
        Dictionary defining keyword arguments provided to ``target``.

    :arg name:
        Forwarded to ``multiprocessing.Process.name``.

    :arg daemon:
        Forwarded to ``multiprocessing.Process.daemon``.

    :returns:
        :class:`gipc._GProcess` instance (inherits from
        ``multiprocessing.Process`` and re-implements some of its methods in a
        gevent-cooperative fashion).

    Process creation is based on ``multiprocessing.Process()``. When working
    with gevent, it is highly recommended to start child processes in no other
    way than via via :func:`start_process`. It triggers most of the magic
    behind ``gipc``.
    """
    if not isinstance(args, tuple):
        raise TypeError('`args` must be tuple.')
    if not isinstance(kwargs, dict):
        raise TypeError('`kwargs` must be dictionary.')
    log.debug("Invoke target `%s` in child process." % target)
    childhandles = list(_filter_handles(chain(args, kwargs.values())))
    if WINDOWS:
        for h in childhandles:
            h._pre_createprocess_windows()
    p = _GProcess(
        target=_child,
        name=name,
        kwargs={"target": target,
                "args": args,
                "kwargs": kwargs})
    if daemon is not None:
        p.daemon = daemon
    p.start()
    p.start = lambda *a, **b: sys.stderr.write(
        "gipc WARNING: Redundant call to %s.start()\n" % p)
    # Close dispensable file handles in parent.
    for h in childhandles:
        log.debug("Invalidate %s in parent." % h)
        if WINDOWS:
            h._post_createprocess_windows()
        h.close()
    return p


def _child(target, args, kwargs):
    """Wrapper function that runs in child process. Resets gevent/libev state
    and executes user-given function.

    After fork on POSIX-compliant systems, gevent's state is inherited by the
    child which may lead to undesired behavior, such as greenlets running in
    both, the parent and the child. Therefore, on Unix, gevent's and libev's
    state is reset before running the user-given function.
    """
    log.debug("_child start. target: `%s`" % target)
    childhandles = list(_filter_handles(chain(args, kwargs.values())))
    if not WINDOWS:
        # `gevent.reinit` calls `libev.ev_loop_fork()`, which reinitialises
        # the kernel state for backends that have one. Must be called in the
        # child before using further libev API.
        gevent.reinit()
        log.debug("Delete current hub's threadpool.")
        hub = gevent.get_hub()
        # Delete threadpool before hub destruction, otherwise `hub.destroy()`
        # might block forever upon `ThreadPool.kill()` as of gevent 1.0rc2.
        del hub.threadpool
        hub._threadpool = None
        # Destroy default event loop via `libev.ev_loop_destroy()` and delete
        # hub. This dumps all registered events and greenlets that have been
        # duplicated from the parent via fork().
        log.debug("Destroy hub and default loop.")
        hub.destroy(destroy_loop=True)
        # Create a new hub and a new default event loop via
        # `libev.gevent_ev_default_loop`.
        h = gevent.get_hub(default=True)
        log.debug("Created new hub and default event loop.")
        assert h.loop.default, 'Could not create libev default event loop.'
        # On Unix, file descriptors are inherited by default. Also, the global
        # `_all_handles` is inherited from the parent. Close dispensable file
        # descriptors in child.
        for h in _all_handles[:]:
            if not h in childhandles:
                log.debug("Invalidate %s in child." % h)
                h._set_legit_process()
                # At duplication time the handle might have been locked.
                # Unlock.
                h._lock.counter = 1
                h.close()
    else:
        # On Windows, the state of module globals is not transferred to
        # children. Set `_all_handles`.
        _set_all_handles(childhandles)
    # `_all_handles` now must contain only those handles that have been
    # transferred to the child on purpose.
    for h in _all_handles:
        assert h in childhandles
    # Register transferred handles for current process.
    for h in childhandles:
        h._set_legit_process()
        if WINDOWS:
            h._post_createprocess_windows()
        log.debug("Handle `%s` is now valid in child." % h)
    # Invoke user-given function.
    target(*args, **kwargs)
    # Close file descriptors before exiting process. Needless, but clean.
    for h in childhandles:
        try:
            # The user might already have closed it.
            h.close()
        except GIPCClosed:
            pass


class _GProcess(multiprocessing.Process):
    """
    Compatible with the ``multiprocessing.Process`` API.

    For cooperativeness with gevent and compatibility with libev, it currently
    re-implements ``start()``, ``is_alive()``, ``exitcode`` on Unix and
    ``join()`` on Windows as well as on Unix.

    .. note::

        On Unix, child monitoring is implemented via libev child watchers.
        To that end, libev installs its own SIGCHLD signal handler.
        Any call to ``os.waitpid()`` would compete with that handler, so it
        is not recommended to call it in the context of this module.
        ``gipc`` prevents ``multiprocessing`` from calling ``os.waitpid()`` by
        monkey-patching ``multiprocessing.forking.Popen.poll`` to always return
        ``None``. Calling ``gipc._GProcess.join()`` is not required for
        cleaning up after zombies (libev does). It just waits until the process
        has terminated.
    """
    # Remarks regarding child process monitoring on Unix:
    #
    # For each `_GProcess`, a libev child watcher is started in the modified
    # `start()` method below. The modified `join()` method is adjusted to this
    # libev child watcher-based child monitoring.
    # `multiprocessing.Process.join()` is entirely surpassed, but resembled.
    #
    # After initialization of the first libev child watcher, i.e. after
    # initialization of the first _GProcess instance, libev handles SIGCHLD
    # signals. Dead children become reaped by the libev event loop. The
    # children's status code is evaluated by libev. In conclusion, installation
    # of the libev SIGCHLD handler renders multiprocessing's child monitoring
    # useless and even hindering.
    #
    # Any call to os.waitpid can make libev miss certain SIGCHLD
    # events. According to
    # http://pubs.opengroup.org/onlinepubs/009695399/functions/waitpid.html
    #
    # "If [...] the implementation queues the SIGCHLD signal, then if wait()
    #  or waitpid() returns because the status of a child process is available,
    #  any pending SIGCHLD signal associated with the process ID of the child
    #  process shall be discarded."
    #
    # On Windows, cooperative `join()` is realized via frequent non-blocking
    # calls to `Process.is_alive()` and the original `join()` method.
    if not WINDOWS:
        # multiprocessing.process.Process.start() and other methods may
        # call multiprocessing.process._cleanup(). This and other mp methods
        # may call multiprocessing.forking.Popen.poll() which itself invokes
        # os.waitpid(). In extreme cases (high-frequent child process
        # creation, short-living child processes), this competes with libev's
        # SIGCHLD handler and may win, resulting in libev not being able to
        # retrieve all SIGCHLD signals corresponding to started children. This
        # could make certain _GProcess.join() calls block forever.
        # -> Prevent multiprocessing.forking.Popen.poll() from calling
        # os.waitpid(). Let libev do the job.
        multiprocessing.forking.Popen.poll = lambda *a, **b: None

        def start(self):
            # Start grabbing SIGCHLD in libev event loop.
            gevent.get_hub().loop.install_sigchld()
            # Run new process (based on `fork()` on POSIX-compliant systems).
            super(_GProcess, self).start()
            # The occurrence of SIGCHLD is recorded asynchronously in libev.
            # This guarantees proper behaviour even if the child watcher is
            # started after the child exits. Start child watcher now.
            self._sigchld_watcher = gevent.get_hub().loop.child(self.pid)
            self._returnevent = gevent.event.Event()
            self._sigchld_watcher.start(
                self._on_sigchld, self._sigchld_watcher)
            log.debug("SIGCHLD watcher for %s started." % self.pid)

        def _on_sigchld(self, watcher):
            """Callback of libev child watcher. Called when libev event loop
            catches corresponding SIGCHLD signal.
            """
            watcher.stop()
            # Status evaluation copied from `multiprocessing.forking`.
            if os.WIFSIGNALED(watcher.rstatus):
                self._popen.returncode = -os.WTERMSIG(watcher.rstatus)
            else:
                assert os.WIFEXITED(watcher.rstatus)
                self._popen.returncode = os.WEXITSTATUS(watcher.rstatus)
            self._returnevent.set()
            log.debug(("SIGCHLD watcher callback for %s invoked. Exitcode "
                       "stored: %s" % (self.pid, self._popen.returncode)))

        def is_alive(self):
            assert self._popen is not None, "Process not yet started."
            if self._popen.returncode is None:
                return True
            return False

        @property
        def exitcode(self):
            if self._popen is None:
                return None
            return self._popen.returncode

        def __repr__(self):
            """Based on original __repr__ from Python 2.7's mp package.
            """
            status = 'started'
            if self.exitcode is not None:
                status = self.exitcode
            return '<%s(%s, %s%s)>' % (
                type(self).__name__, self._name, status,
                self._daemonic and ' daemon' or '')

    def join(self, timeout=None):
        """
        Wait cooperatively until child process terminates or timeout occurs.

        :arg timeout: ``None`` (default) or a a time in seconds. The method
            simply returns upon timeout expiration. The state of the process
            has to be identified via ``is_alive()``.
        """
        assert self._parent_pid == os.getpid(), "I'm not parent of this child."
        assert self._popen is not None, 'Can only join a started process.'
        if not WINDOWS:
            # Resemble multiprocessing's join() method while replacing
            # `self._popen.wait(timeout)` with
            # `self._returnevent.wait(timeout)`
            self._returnevent.wait(timeout)
            if self._popen.returncode is not None:
                multiprocessing.process._current_process._children.discard(
                    self)
            return
        with gevent.Timeout(timeout, False):
            while self.is_alive():
                # Is the polling frequency reasonable?
                gevent.sleep(0.01)
        # Clean up after child as designed by Process class (non-blocking).
        super(_GProcess, self).join(timeout=0)


class _GIPCHandle(object):
    """
    The ``_GIPCHandle`` class implements common features of read and write
    handles. ``_GIPCHandle`` instances are created via :func:`pipe`.

    .. todo::

        Implement destructor?
        http://eli.thegreenplace.net/2009/06/12/
        safely-using-destructors-in-python/
    """
    def __init__(self):
        global _all_handles
        self._id = os.urandom(3).encode("hex")
        self._legit_pid = os.getpid()
        self._make_nonblocking()
        self._lock = gevent.lock.Semaphore(value=1)
        self._closed = False
        _all_handles.append(self)

    def _make_nonblocking(self):
        if hasattr(gevent.os, 'make_nonblocking'):
            # On POSIX-compliant systems, the file descriptor flags are
            # inherited after forking, i.e. it is sufficient to make fd
            # nonblocking only once.
            gevent.os.make_nonblocking(self._fd)

    def close(self):
        """Close underlying file descriptor and de-register handle for further
        usage. Is called on context exit.

        Raises:
            - :exc:`GIPCError`
            - :exc:`GIPCClosed`
            - :exc:`GIPCLocked`
        """
        global _all_handles
        self._validate()
        if not self._lock.acquire(blocking=False):
            raise GIPCLocked(
                "Can't close handle %s: locked for I/O operation." % self)
        log.debug("Invalidating %s ..." % self)
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        if self in _all_handles:
            # Remove the handle from the global list of valid handles.
            _all_handles.remove(self)
        self._closed = True
        self._lock.release()

    def _set_legit_process(self):
        log.debug("Legitimate %s for current process." % self)
        self._legit_pid = os.getpid()

    def _validate(self):
        """Raise exception if this handle is closed or not registered to be
        used in the current process.

        Intended to be called before every operation on `self._fd`.
        Reveals wrong usage of this module in the context of multiple
        processes. Might prevent tedious debugging sessions. Has little
        performance impact.
        """
        if self._closed:
            raise GIPCClosed(
                "GIPCHandle has been closed before.")
        if os.getpid() != self._legit_pid:
            raise GIPCError(
                "GIPCHandle %s not registered for current process %s." % (
                self, os.getpid()))

    def _pre_createprocess_windows(self):
        """Prepare file descriptor for transfer to child process on Windows.

        By default, file descriptors are not inherited by child processes on
        Windows. However, they can be made inheritable via calling the system
        function `DuplicateHandle` while setting `bInheritHandle` to True.
        From MSDN:
            bInheritHandle:
                A variable that indicates whether the handle is inheritable.
                If TRUE, the duplicate handle can be inherited by new processes
                created by the target process. If FALSE, the new handle cannot
                be inherited.
        The Python `subprocess` and `multiprocessing` modules make use of this.
        There is no Python API officially exposed. However, the function
        `multiprocessing.forking.duplicate` is available since the introduction
        of the multiprocessing module in Python 2.6 up to the development
        version of Python 3.4 as of 2012-10-20.
        """
        if WINDOWS:
            from multiprocessing.forking import duplicate
            # Get Windows file handle from C file descriptor.
            h = msvcrt.get_osfhandle(self._fd)
            # Duplicate file handle, rendering the duplicate inheritable by
            # processes created by the current process.
            self._ihfd = duplicate(handle=h, inheritable=True)
            # Close "old" (in-inheritable) file descriptor.
            os.close(self._fd)
            self._fd = False

    def _post_createprocess_windows(self):
        """Restore file descriptor on Windows.
        """
        if WINDOWS:
            # Get C file descriptor from Windows file handle.
            self._fd = msvcrt.open_osfhandle(self._ihfd, self._fd_flag)
            del self._ihfd

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.close()
        except GIPCClosed:
            # Tolerate handles that have been closed within context.
            pass
        except GIPCLocked:
            # Locked for I/O outside of context, which is not fine.
            raise GIPCLocked((
                "Context manager can't close handle %s. It's locked for I/O "
                "operation out of context." % self))

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        fd = self._fd
        if hasattr(self, "_ihfd"):
            fd = "WIN_%s" % self._ihfd
        return "<%s_%s fd: %s>" % (self.__class__.__name__, self._id, fd)


class _GIPCReader(_GIPCHandle):
    """
    A ``_GIPCReader`` instance manages the read end of a pipe. It is created
    via :func:`pipe`.
    """
    def __init__(self, pipe_read_fd):
        self._fd = pipe_read_fd
        self._fd_flag = os.O_RDONLY
        _GIPCHandle.__init__(self)
        self._timeout = None

    def _recv_in_buffer(self, n):
        """Cooperatively read `n` bytes from file descriptor to buffer."""
        readbuf = io.BytesIO()
        remaining = n
        while remaining > 0:
            chunk = _READ_NB(self._fd, remaining)
            received = len(chunk)
            if received == 0:
                if remaining == n:
                    raise EOFError(
                        "Most likely, the other pipe end is closed.")
                else:
                    raise IOError("Message interrupted by EOF.")
            readbuf.write(chunk)
            remaining -= received
        return readbuf

    def get(self, timeout=None):
        """Receive and return an object from the pipe. Block
        gevent-cooperatively until object is available or timeout expires.

        :arg timeout: ``None`` (default) or a ``gevent.Timeout``
            instance. The timeout must be started to take effect and is
            cancelled when the first byte of a new message arrives (i.e.
            providing a timeout does not guarantee that the method completes
            within the timeout interval).

        :returns: a Python object.

        Raises:
            - :exc:`gevent.Timeout` (if provided)
            - :exc:`GIPCError`
            - :exc:`GIPCClosed`
            - :exc:`pickle.UnpicklingError`

        Recommended usage for silent timeout control::

            with gevent.Timeout(TIME_SECONDS, False) as t:
                reader.get(timeout=t)

        .. warning::

            The timeout control is currently not available on Windows,
            because Windows can't apply select() to pipe handles.
            An ``OSError`` is expected to be raised in case you set a
            timeout.
        """
        self._validate()
        with self._lock:
            if timeout:
                # Wait for ready-to-read event.
                h = gevent.get_hub()
                h.wait(h.loop.io(self._fd, 1))
                timeout.cancel()
            msize, = struct.unpack("!i", self._recv_in_buffer(4).getvalue())
            bindata = self._recv_in_buffer(msize).getvalue()
        return pickle.loads(bindata)


class _GIPCWriter(_GIPCHandle):
    """
    A ``_GIPCWriter`` instance manages the write end of a pipe. It is created
    via :func:`pipe`.
    """
    def __init__(self, pipe_write_fd):
        self._fd = pipe_write_fd
        self._fd_flag = os.O_WRONLY
        _GIPCHandle.__init__(self)

    def _write(self, bindata):
        """Write `bindata` to pipe in a gevent-cooperative manner.

        POSIX-compliant system notes (http://linux.die.net/man/7/pipe:):
            - Since Linux 2.6.11, the pipe capacity is 65536 bytes
            - Relevant for large messages (O_NONBLOCK enabled,
              n > PIPE_BUF (4096 Byte, usually)):
                "If the pipe is full, then write(2) fails, with errno set
                to EAGAIN. Otherwise, from 1 to n bytes may be written (i.e.,
                a "partial write" may occur; the caller should check the
                return value from write(2) to see how many bytes were
                actualy written), and these bytes may be interleaved with
                writes by other processes."

            EAGAIN is handled within _WRITE_NB; partial writes here.
        """
        while True:
            # Causes OSError when read end is closed (broken pipe).
            diff = len(bindata) - _WRITE_NB(self._fd, bindata)
            if not diff:
                break
            bindata = bindata[-diff:]

    def put(self, o):
        """Pickle object ``o`` and write it to the pipe. Block
        gevent-cooperatively until all data is written.

        :arg o: a pickleable Python object.

        Raises:
            - :exc:`GIPCError`
            - :exc:`GIPCClosed`
            - :exc:`pickle.PicklingError`

        """
        self._validate()
        with self._lock:
            bindata = pickle.dumps(o, pickle.HIGHEST_PROTOCOL)
            # TODO: one write instead of two?
            self._write(struct.pack("!i", len(bindata)))
            self._write(bindata)


class _PairContext(tuple):
    """
    Generic context manager for a 2-tuple containing two entities supporting
    context enter and exit themselves. Returns 2-tuple upon entering the
    context, attempts to exit both tuple elements upon context exit.
    """
    def __init__(self, (e1, e2)):
        self._e1 = e1
        self._e2 = e2
        super(_PairContext, self).__init__((e1, e2))

    def __enter__(self):
        for e in self:
            e.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Call `__exit__()` for both, e1 and e2 entities, in any case,
        as expected of a context manager. Exit e2 first, as it is used as
        writer in case of `_PairContext((reader1, writer1))` and
        `os.close()` on reader might block on Windows otherwise.
        If an exception occurs during e2 exit, store it, exit e1 and raise it
        afterwards. If an exception is raised during both, e1 and e2 exit, only
        raise the e1 exit exception.
        """
        e2_exit_exception = None
        try:
            self._e2.__exit__(exc_type, exc_value, traceback)
        except:
            e2_exit_exception = sys.exc_info()
        self._e1.__exit__(exc_type, exc_value, traceback)
        if e2_exit_exception:
            raise e2_exit_exception[1], None, e2_exit_exception[2]


class _GIPCDuplexHandle(_PairContext):
    """
    A ``_GIPCDuplexHandle`` instance manages one end of a bidirectional
    pipe-based message transport created via :func:`pipe()` with
    ``duplex=True``. It provides ``put()``, ``get()``, and ``close()``
    methods which are forwarded to the corresponding methods of
    :class:`gipc._GIPCWriter` and :class:`gipc._GIPCReader`.
    """
    def __init__(self, (reader, writer)):
        self._reader = reader
        self._writer = writer
        self.put = self._writer.put
        self.get = self._reader.get
        super(_GIPCDuplexHandle, self).__init__((reader, writer))

    def close(self):
        """Close associated `_GIPCHandle` instances. Tolerate if one of both
        has already been closed before. Throw GIPCClosed if both have been
        closed before.
        """
        if self._writer._closed and self._reader._closed:
            raise GIPCClosed("Reader & writer in %s already closed." % (self,))
        # Close writer first. Otherwise, reader close would block on Win.
        if not self._writer._closed:
            self._writer.close()
        if not self._reader._closed:
            self._reader.close()

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "<%s(%r, %s)>" % (
            self.__class__.__name__, self._reader, self._writer)


# Define non-blocking read and write functions
if hasattr(gevent.os, 'nb_write'):
    # POSIX system -> use actual non-blocking I/O
    _READ_NB = gevent.os.nb_read
    _WRITE_NB = gevent.os.nb_write
else:
    # Windows -> imitate non-blocking I/O based on gevent threadpool
    _READ_NB = gevent.os.tp_read
    _WRITE_NB = gevent.os.tp_write


def _filter_handles(l):
    """Iterate through `l`, filter and yield `_GIPCHandle` instances.
    """
    for o in l:
        if isinstance(o, _GIPCHandle):
            yield o
        elif isinstance(o, _GIPCDuplexHandle):
            yield o._writer
            yield o._reader


# Container for keeping track of valid `_GIPCHandle`s in current proecss.
_all_handles = []


def _get_all_handles():
    """Return a copy of the list of all handles.
    """
    return _all_handles[:]


def _set_all_handles(handles):
    global _all_handles
    _all_handles = handles
