# -*- coding: utf-8 -*-
#
#   Copyright (C) 2012 Jan-Philip Gehrcke
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
TODO:
    - make reader/writer context manager-aware (close() on __exit__)?
    - implement 'polling' get() based on some kind of fd polling.
      Should raise some kind of WouldBlockException if no data available.
      Difficult (impossible?) to identify complete messages in advance.
    - check if the gevent FileObjectPosix can be of any use
    - review buffer-implementation, consider, buffer(), memoryview(), ..
    - ensure portability between Python 2 and 3
    - hub.cancel_wait() (cf. gevent sockets) in close instead of lock check?
"""

import os
import sys
import logging
import io
import struct
import multiprocessing as mp
import multiprocessing.process as mp_process
import itertools
import signal
try:
   import cPickle as pickle
except:
   import pickle
WINDOWS = sys.platform == "win32"
if WINDOWS:
    import msvcrt

# 3rd party modules
import gevent
import gevent.os
import gevent.lock
import gevent.event


log = logging.getLogger("gpipe")


# Define non-blocking read and write functions
if hasattr(gevent.os, 'nb_write'):
    # POSIX system -> use actual non-blocking I/O
    _READ_NB = gevent.os.nb_read
    _WRITE_NB = gevent.os.nb_write
else:
    # Windows -> imitate non-blocking I/O based on a gevent threadpool
    _READ_NB = gevent.os.tp_read
    _WRITE_NB = gevent.os.tp_write


# Container for keeping track of valid `_GPipeHandle`s
_all_handles = []


def pipe():
    """Create pipe as well as handles for reading and writing.

    Based on os.pipe().
    os.pipe() implementation on Windows:
      - uses CreatePipe(&read, &write, NULL, 0) (http://bit.ly/RDuKUm)
      - creates an anonymous pipe, system handles buffer size.
      - anonymous pipes are implemented using a named pipe with a unique name.
      - asynchronous (overlapped) read and write operations are not supported
        by anonymous pipes.
    os.pipe() on POSIX (http://linux.die.net/man/2/pipe):
      - based on system call pipe(fds)
      - common Linux: pipe buffer is 4096 bytes, pipe capacity is 65536 bytes

    Returns:
        (reader, writer) tuple (both instances of `_GPipeHandle`).
    """
    r, w = os.pipe()
    reader = _GPipeReader(r)
    writer = _GPipeWriter(w)
    _all_handles.append(reader)
    _all_handles.append(writer)
    return reader, writer


def _child(target, all_handles, args, kwargs):
    """Runs in child process. Sanitizes situation in child process and
    executes user-given function.

    `target`: user-given function to be called with `kwargs`
    `childhandles`: GPipeHandles that are intented to be used in child.

    After fork on POSIX systems, gevent's state is inherited by the
    child which may lead to undesired and undefined behavior, such as
    greenlets running in both, the parent and the child. Therefore, on POSIX,
    gevent's state is entirely reset before running the user-given function.
    """
    # Restore `_all_handles` (required on Windows; does not harm elsewhere)
    _all_handles = all_handles
    if not WINDOWS:
        # `gevent.reinit` calls `libev.ev_loop_fork()`, which is designed to
        # be called after fork.
        gevent.reinit()
        # Destroy default event loop via `libev.ev_loop_destroy()` and delete
        # hub. This dumps all registered events and greenlets that have been
        # duplicated from the parent.
        gevent.get_hub().destroy(destroy_loop=True)
        # Create a new hub and a new default event loop via
        # `libev.gevent_ev_default_loop`.
        h = gevent.get_hub(default=True)
        assert h.loop.default, 'Could not create new default event loop.'
    allargs = itertools.chain(args, kwargs.values())
    childhandles = [a for a in allargs if isinstance(a, _GPipeHandle)]
    # Register inherited handles for current process.
    # Close file descriptors that are not intended for further usage.
    for h in _all_handles[:]:
        h._set_legit_process()
        if WINDOWS:
            log.debug("Restore %s in child." % h)
            h._post_createprocess_windows()
        if not h in childhandles:
            log.debug("Invalidate %s in child." % h)
            h.close()
    target(*args, **kwargs)
    for h in childhandles:
        try:
            # The user or a child of this child might already have closen it.
            h.close()
        except GPipeError:
            pass


def start_process(target, name=None, args=(), kwargs={}, daemon=None):
    """Spawn child process with the intention to use `_GPipeHandle`s
    provided via `args`/`kwargs` within the child process. Execute
    target(*args, **kwargs) in the child process.

    Process creation is based on multiprocessing.Process(). When working with
    gevent and gevent-messagepipe, instead of calling Process() on your own,
    it is highly recommended to create child processes via this method.
    It takes care of
        - closing dispensable file descriptors after child process creation.
        - proper file descriptor inheritance on Windows.
        - re-initialization of the gevent event loop in the child process (no
          greenlet spawned in the parent will run in the child) on Unix.
        - making `join()` cooperative

    Args:
        `target`: user-given function to be called with `kwargs`
        `name`: `multiprocessing.Process.name`
        `daemon`: `multiprocessing.Process.daemon`
        `args`: tuple defining positional arguments provided to `target`
        `kwargs`: dictionary defining keyword arguments provided to `target`

    Returns:
        `_GProcess` instance (inherits from `multiprocessing.Process`)
    """
    allargs = itertools.chain(args, kwargs.values())
    childhandles = [a for a in allargs if isinstance(a, _GPipeHandle)]
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
    # Close those file handlers in parent that are not further required.
    for h in childhandles:
        log.debug("Invalidate %s in parent." % h)
        h.close()
    return p


class _GProcess(mp.Process):
    """
    Implements adjustments to multiprocessing's Process class.

    On POSIX, adjust the `join()` implementation to the framework, as we
    cannot rely on
        `multiprocessing.Process._popen.wait()`
    to 'tell the truth' about the state for children of children.
    With the current code base, libev seems to handle SIGCHLD by default in
    children of children. This makes os.waitpid() (used in `_popen.wait()`)
    throw an ECHILD error ("process specified by pid does not exist or is
    not a child of the calling process"), after which multiprocessing's
    `_popen.wait()` returns None, meaning 'alive' even for child processes
    that finished before. This could be rectified via re-installing the
    default signal handler with
        `signal.signal(signal.SIGCHLD, signal.SIG_DFL)`.
    However, doing so would render libev's child watchers useless. Instead,
    for each _GProcess, a libev child watcher is explicitly installed in the
    modified `start()` method below. The modified `join()` method is adjusted
    to this libev-watcher-based child monitoring.
    `multiprocessing.Process.join()` is entirely surpassed, but resembled.

    On Windows, cooperative `join` is realized via frequent non-blocking calls
    to `is_alive` and the original join method.
    """
    if not WINDOWS:
        def start(self):
            self.returncode = None
            hub = gevent.get_hub()
            self._gresult = gevent.event.AsyncResult()
            hub.loop.install_sigchld()
            super(_GProcess, self).start()
            # Is there a race condition? (can it happen that the child already
            # finished before the watcher below is started?)
            self._sigchld_watcher = hub.loop.child(self.pid)
            self._sigchld_watcher.start(
                self._on_sigchld, self._sigchld_watcher)
            log.debug("SIGCHLD watcher for %s installed." % self.pid)

        def _on_sigchld(self, watcher):
            watcher.stop()
            # Status evaluation copied from multiprocessing.forking
            if os.WIFSIGNALED(watcher.rstatus):
                self.returncode = -os.WTERMSIG(watcher.rstatus)
            else:
                assert os.WIFEXITED(watcher.rstatus)
                self.returncode = os.WEXITSTATUS(watcher.rstatus)
            self._gresult.set(self.returncode)
            log.debug(("SIGCHLD watcher callback for %s invoked. Returncode "
                       "stored: %s" % (self.pid, self.returncode)))

    def join(self, timeout=None):
        """
        Wait cooperatively until child process terminates or timeout ocurrs.
        """
        if not WINDOWS:
            # Resemble multiprocessing's join() method while replacing
            # `self._popen.wait(timeout)` with
            # `self._gresult.wait(timeout)`
            assert self._parent_pid == os.getpid(),(
                'Can only join a child process.')
            assert self._popen is not None,(
                'Can only join a started process.')
            self._gresult.wait(timeout=timeout)
            if self.returncode is not None:
                mp_process._current_process._children.discard(self)
            return

        with gevent.Timeout(timeout, False):
            while self.is_alive():
                gevent.sleep(0.05)
        # Clean up after child as designed by Process class (non-blocking).
        super(_GProcess, self).join(timeout=0)


class GPipeError(Exception):
    pass


class _GPipeHandle(object):
    def __init__(self):
        self._id = os.urandom(3).encode("hex")
        self._legit_pid = os.getpid()
        self._make_nonblocking()
        self._lock = gevent.lock.Semaphore(value=1)
        self._closed = False

    def _make_nonblocking(self):
        if hasattr(gevent.os, 'make_nonblocking'):
            # On POSIX, file descriptor flags are inherited after forking,
            # i.e. it is sufficient to make them nonblocking once (in parent).
            gevent.os.make_nonblocking(self._fd)

    def close(self):
        """Close file descriptor and de-register handle for further usage.

        Closes underlying file descriptor and removes the handle from the
        list of valid handles.
        """
        self._validate_process()
        if not self._lock.acquire(blocking=False):
            raise GPipeError("Can't close: handle locked for I/O operation.")
        log.debug("Invalidating %s ..." % self)
        self._closed = True
        if self._fd is not None:
            log.debug("os.close(%s)" % self._fd)
            os.close(self._fd)
            self._fd = None
        if self in _all_handles:
            log.debug("Remove %s from _all_handles" % self)
            _all_handles.remove(self)
        self._lock.release()

    def _set_legit_process(self):
        log.debug("Legitimate %s for current process." % self)
        self._legit_pid = os.getpid()

    def _validate_process(self):
        """Raise exception if this handle is not registered to be used in
        the current process.

        Intended to be called before every operation on `self._fd`.
        Reveals wrong usage of this module in the context of multiple
        processes. Might prevent tedious debugging sessions.
        Has little performance impact, as getpid() system call ist very fast.
        """
        if self._closed:
            raise GPipeError(
                "GPipeHandle has been closed before.")
        if os.getpid() != self._legit_pid:
            raise GPipeError(
                "GPipeHandle not registered for current process.")

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
        version of Python 3.4 as of 2012-10-20. The code below is influenced by
        multiprocessing's forking.py.
        """
        if WINDOWS:
            from mp.forking import duplicate
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

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        fd = self._fd
        if hasattr(self, "_ihfd"):
            fd = "WIN_%s" % self._ihfd
        return "<%s_%s fd: %s>" % (self.__class__.__name__, self._id, fd)


class _GPipeReader(_GPipeHandle):
    def __init__(self, pipe_read_fd):
        self._fd = pipe_read_fd
        self._fd_flag = os.O_RDONLY
        _GPipeHandle.__init__(self)

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

    def get(self):
        """Receive and return (un)picklelable object from pipe.

        Blocks cooperatively until message is available.
        TODO: timeout option"""
        self._validate_process()
        with self._lock:
            msize, = struct.unpack("!i", self._recv_in_buffer(4).getvalue())
            bindata = self._recv_in_buffer(msize).getvalue()
            return pickle.loads(bindata)


class _GPipeWriter(_GPipeHandle):
    def __init__(self, pipe_write_fd):
        self._fd = pipe_write_fd
        self._fd_flag = os.O_WRONLY
        _GPipeHandle.__init__(self)

    def _write(self, bindata):
        """Write `bindata` to pipe in a gevent-cooperative manner.

        POSIX notes (http://linux.die.net/man/7/pipe:):
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
            diff = len(bindata) - _WRITE_NB(self._fd, bindata)
            if not diff:
                break
            bindata = bindata[-diff:]

    def put(self, o):
        """Put pickleable object into the pipe. Block cooperatively."""
        self._validate_process()
        with self._lock:
            bindata = pickle.dumps(o, pickle.HIGHEST_PROTOCOL)
            # TODO: one write instead of two?
            self._write(struct.pack("!i", len(bindata)))
            self._write(bindata)

