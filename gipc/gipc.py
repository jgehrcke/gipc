# -*- coding: utf-8 -*-
#
#   Copyright (C) 2012 - 2013 Jan-Philip Gehrcke
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
.. todo::

    - Implement poll/peek on read end. (It's impossible to identify complete
      messages in advance, but within the framework only complete messages
      are sent.)
    - Can gevent's FileObjectPosix be of any use?
    - Review buffer-implementation, consider, buffer() and memoryview().
    - hub.cancel_wait() (cf. gevent sockets) in close instead of lock check?
    - Work on portability between Python 2 and 3.
    - put() timeout? Relevant in case of pipe being full. However, put()
      duration cannot be controlled if write is blocking *after* partial
      msg write. Doesn't make sense I think.
    - Implementation on Windows based on NamedPipes with overlapping IO
      could give useful control. Use libuv as backend instead of libev?
"""

import os
import sys
import io
import struct
import itertools
import signal
import logging
import multiprocessing
import multiprocessing.forking
import multiprocessing.process
try:
   import cPickle as pickle
except:
   import pickle
WINDOWS = sys.platform == "win32"
if WINDOWS:
    import msvcrt
import gevent
import gevent.os
import gevent.lock
import gevent.event


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


def pipe():
    """Creates a new pipe and returns its corresponding read and write
    handles. Those allow for sending and receiving pickleable objects through
    the pipe in a gevent-cooperative manner. A handle-pair can transmit
    data between greenlets within one process or across processes created via
    :func:`start_process`.

    :returns:
        ``(reader, writer)`` tuple. Both items are instances of
        :class:`gipc._GIPCHandle`.

    :class:`gipc._GIPCHandle` instances are recommended to be used with Python's
    context manager in the following ways::

        with pipe() as (r, w):
            do_something(r, w)

    ::

        reader, writer = pipe()

        with reader:
            do_something(reader)

        with writer as w:
            do_something(w)

    The transport layer is based on ``os.pipe()`` (i.e. ``CreatePipe()`` on
    Windows and ``pipe()`` on POSIX-compliant systems).
    """
    # os.pipe() implementation on Windows (http://bit.ly/RDuKUm):
    #   - CreatePipe(&read, &write, NULL, 0)
    #   - anonymous pipe, system handles buffer size
    #   - anonymous pipes are implemented using named pipes with unique names
    #   - asynchronous (overlapped) read and write operations not supported
    # os.pipe() implementation on Unix (http://linux.die.net/man/7/pipe):
    #   - based on pipe()
    #   - common Linux: pipe buffer is 4096 bytes, pipe capacity is 65536 bytes
    r, w = os.pipe()
    reader = _GIPCReader(r)
    writer = _GIPCWriter(w)
    _all_handles.append(reader)
    _all_handles.append(writer)
    return _HandlePairContext((reader, writer))


def start_process(target, args=(), kwargs={}, daemon=None, name=None):
    """Spawn child process and execute function ``target(*args, **kwargs)``.
    Any existing :class:`gipc._GIPCHandle` can be handed over to the child
    process via ``args`` and/or ``kwargs``.

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
    with gevent, instead of calling ``Process()`` directly, it is highly
    recommended to start child processes via :func:`start_process`. It takes
    care of

        - re-initializing gevent and libev's event loop in the child process.
        - closing dispensable file descriptors after child process creation.
        - proper file descriptor inheritance on Windows.
        - providing cooperative process methods (such as ``join()``).

    Calling this method breaks ``os.waitpid()`` on Unix: spawning the first
    child activates libev child watchers, leading to libev reap children in the
    moment they die. Applied to such a child, ``os.waitpid()`` throws
    ``ECHILD`` (cf. http://linux.die.net/man/2/waitid).
    """
    if not isinstance(args, tuple):
        raise TypeError, '`args` must be tuple.'
    if not isinstance(kwargs, dict):
        raise TypeError, '`kwargs` must be dictionary.'
    log.debug("Invoke target `%s` in child process." % target)
    allargs = itertools.chain(args, kwargs.values())
    childhandles = [a for a in allargs if isinstance(a, _GIPCHandle)]
    if WINDOWS:
        for h in _all_handles:
            h._pre_createprocess_windows()
    p = _GProcess(
        target=_child,
        name=name,
        kwargs={"target": target,
                "all_handles": _all_handles,
                "args": args,
                "kwargs": kwargs})
    if daemon is not None:
        p.daemon = daemon
    p.start()
    if WINDOWS:
        for h in _all_handles:
            h._post_createprocess_windows()
    # Close dispensable file handles in parent.
    for h in childhandles:
        log.debug("Invalidate %s in parent." % h)
        h.close()
    return p


def _child(target, all_handles, args, kwargs):
    """Wrapper function that runs in child process. Resets gevent/libev state
    and executes user-given function.

    After fork on POSIX-compliant systems, gevent's state is inherited by the
    child which may lead to undesired behavior, such as greenlets running in
    both, the parent and the child. Therefore, on Unix, gevent's and libev's
    state is reset before running the user-given function.
    """
    log.debug("_child start. target: `%s`" % target)
    # Restore global `_all_handles` (required on Win, does not harm elsewhere).
    # (The value of a global variable set in the parent process is not
    #  propagated to children on Windows (as is on Unix via fork())).
    global _all_handles
    _all_handles = all_handles
    if not WINDOWS:
        # `gevent.reinit` calls `libev.ev_loop_fork()`, which reinitialises
        # the kernel state for backends that have one. Must be called in the
        # child before using further libev API.
        gevent.reinit()
        log.debug("Delete current hub's threadpool.")
        hub = gevent.get_hub()
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
    allargs = itertools.chain(args, kwargs.values())
    childhandles = [a for a in allargs if isinstance(a, _GIPCHandle)]
    # Register inherited handles for current process. Close those that are not
    # intended for further usage.
    for h in _all_handles[:]:
        h._set_legit_process()
        if WINDOWS:
            h._post_createprocess_windows()
        if not h in childhandles:
            log.debug("Invalidate %s in child." % h)
            h.close()
            continue
        log.debug("Handle `%s` is valid in child." % h)
    target(*args, **kwargs)
    for h in childhandles:
        try:
            # The user or a child of this child might already have closed it.
            h.close()
        except GIPCClosed:
            pass


class _GProcess(multiprocessing.Process):
    """
    Implements adjustments to multiprocessing's Process class for
    gevent-cooperativity. Currently re-implements ``start()``, ``is_alive()``,
    ``exitcode`` on Unix and ``join()`` on Windows and Unix.
    """
    #On Unix, we  cannot rely on `multiprocessing.Process.is_alive()` and
    #`multiprocessing.Process._popen.wait()` to tell the truth about the state
    #of children of children:

    #In the initial process, gevent makes libev's default event loop not
    #reap dead children. In children, however, after initialization of the
    #libev default event loop, dead children (grandchildren of the initial
    #process) become reaped immediately by the event loop.

    #This makes `os.waitpid(grandchild_pid)` throw an ECHILD error (process
    #specified by pid does not exist or is not a child of the calling process).
    #This leads to multiprocessing's `_popen.wait()` returning `None`, meaning
    #'alive' -- for child processes that does not exist anymore.

    #Immediate child reaping by libev could be rectified via re-installing
    #the default signal handler with `signal(signal.SIGCHLD, signal.SIG_DFL)`.
    #However, doing so would render libev's child watchers useless.

    #Instead, for each `_GProcess`, a libev child watcher is explicitly
    #started in the modified `start()` method below. The modified `join()`
    #method is adjusted to this libev-watcher-based child monitoring.
    #`multiprocessing.Process.join()` is entirely surpassed, but resembled.
    #`os.waitpid()` is broken in all process generations after the first
    #`_GProcess` has been started.

    #On Windows, cooperative `join()` is realized via frequent non-blocking
    #calls to `Process.is_alive()` and the original `join()` method.
    if not WINDOWS:
        def start(self):
            hub = gevent.get_hub()
            self._returnevent = gevent.event.Event()
            # Start grabbing SIGCHLD in libev event loop.
            hub.loop.install_sigchld()
            # Run new process (based on `fork()` on POSIX-compliant systems).
            super(_GProcess, self).start()
            # The occurrence of SIGCHLD is recorded asynchronously in libev.
            # This guarantees proper behaviour even if the child watcher is
            # started after the child exits. Start child watcher now.
            self._sigchld_watcher = hub.loop.child(self.pid)
            self._sigchld_watcher.start(
                self._on_sigchld, self._sigchld_watcher)
            log.debug("SIGCHLD watcher for %s started." % self.pid)

        def _on_sigchld(self, watcher):
            watcher.stop()
            # Status evaluation taken from `multiprocessing.forking`.
            if os.WIFSIGNALED(watcher.rstatus):
                self._popen.returncode = -os.WTERMSIG(watcher.rstatus)
            else:
                assert os.WIFEXITED(watcher.rstatus)
                self._popen.returncode = os.WEXITSTATUS(watcher.rstatus)
            self._returnevent.set()
            log.debug(("SIGCHLD watcher callback for %s invoked. Exitcode "
                       "stored: %s" % (self.pid, self._popen.returncode)))

        def is_alive(self):
            if self._popen.returncode is None:
                return True
            return False

        @property
        def exitcode(self):
            return self._popen.returncode

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

        Care about destructor?
        http://eli.thegreenplace.net/2009/06/12/
        safely-using-destructors-in-python/
    """
    def __init__(self):
        self._id = os.urandom(3).encode("hex")
        self._legit_pid = os.getpid()
        self._make_nonblocking()
        self._lock = gevent.lock.Semaphore(value=1)
        self._closed = False

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
        self._closed = True
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        if self in _all_handles:
            # Remove the handle from the global list of valid handles.
            _all_handles.remove(self)
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
        """Restore file descriptor on Windows."""
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
            # Closed before, which is fine.
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
        self._newmessage_lengthreceived = False
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
            self._newmessage_lengthreceived = True
            bindata = self._recv_in_buffer(msize).getvalue()
            self._newmessage_lengthreceived = False
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


class _HandlePairContext(tuple):
    def __init__(self, (reader, writer)):
        self.reader = reader
        self.writer = writer
        super(_HandlePairContext, self).__init__((reader, writer))

    def __enter__(self):
        for h in self:
            h.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Call `__exit__()` for both, read and write handles, in any case,
        as expected of a context manager. Exit writer first, as `os.close()`
        on reader might block on Windows otherwise. If an exception occurs
        during writer exit, store it, exit reader and raise it afterwards. If
        an exception is raised during both, reader and writer exit, only
        raise the reader exit exception.
        """
        writer_exit_exception = None
        try:
            self.writer.__exit__(exc_type, exc_value, traceback)
        except:
            writer_exit_exception = sys.exc_info()
        self.reader.__exit__(exc_type, exc_value, traceback)
        if writer_exit_exception:
            raise writer_exit_exception[1], None, writer_exit_exception[2]


# Define non-blocking read and write functions
if hasattr(gevent.os, 'nb_write'):
    # POSIX system -> use actual non-blocking I/O
    _READ_NB = gevent.os.nb_read
    _WRITE_NB = gevent.os.nb_write
else:
    # Windows -> imitate non-blocking I/O based on gevent threadpool
    _READ_NB = gevent.os.tp_read
    _WRITE_NB = gevent.os.tp_write


# Define container for keeping track of valid `_GIPCHandle`s.
_all_handles = []


def get_all_handles():
    return _all_handles[:]


def set_all_handles(handles):
    global _all_handles
    _all_handles = handles


