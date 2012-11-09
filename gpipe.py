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
    - make reader/writer context manager-compatible (close() on exit)?
"""

import os
import sys
import logging
import io
import struct
import multiprocessing
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


def _child(target, childhandles, all_handles, kwargs):
    """(Runs in child process) Sanitize situation in child process and
    execute user-given function.

    `target`: user-given function to be called with `kwargs`
    `childhandles`: GPipeHandles that are intented to be used in child.
    """
    # Restore `_all_handles` (required on Windows; does not harm elsewhere)
    _all_handles = all_handles
    if not WINDOWS:
        # Clean up after fork
        # Call `libev.ev_loop_fork()`: required after fork
        gevent.reinit()
        # Destroy default event loop via `libev.ev_loop_destroy()` and delete
        # hub. This gets rid of all registered events
        # and greenlets that have been duplicated from the parent.
        gevent.get_hub().destroy(destroy_loop=True)
        # Create a fresh event loop via `ev_loop_new` and a new hub.
        gevent.get_hub()
    # Register inherited handles for current process.
    # Close file descriptors that are not intended for further usage.
    log.debug("all handles: %s" % _all_handles)
    for h in _all_handles[:]:
        h._set_legit_process()
        if WINDOWS:
            log.debug("Restore %s in child." % h)
            h._post_createprocess_windows()
        if not h in childhandles:
            log.debug("Remove %s in child." % h)
            h.close()
    target(*childhandles, **kwargs)
    # Close childhandles here?


def start_process(childhandles, target, name=None, kwargs={}, daemon=None):
    """Spawn child process with the intention to use the `_GPipeHandle`s
    provided via `childhandles` within the child process. Execute
    target(*childhandles, **kwargs) in the child process. Similar to
    `multiprocessing.Process()` interface.

    Process creation is based on multiprocessing.Process(). When working with
    gevent and gevent-messagepipe, instead of calling Process() on your own,
    it is highly recommended to create child processes via this method.
    It takes care of
        - closing dispensable file descriptors after child process creation.
        - proper file descriptor inheritance on Windows.
        - re-initialization of the gevent event loop in the child process (no
          greenlet spawned in the parent will run in the child) on Unix.

    Example:
        def childfunction(reader, foo):
            s = reader.get()
            print s, foo # prints "hello to child bar"

        reader, writer = gpipe.pipe()
        p = gpipe.start_process(reader, childfunction, kwargs={'foo': 'bar'})
        writer.put("hello to child")
        p.join()

    Args:
        `childhandles`: `GPipeHandle` or list or tuple of `GPipeHandle`s
            that is/are intented to be used in the child. Unusable in
            parent afterwards.
        `target`: user-given function to be called with `kwargs`
        `name`: `multiprocessing.Process.name`
        `daemon`: `multiprocessing.Process.daemon`
        `kwargs`: dictionary defining keyword arguments provided to `target`

    Returns:
        `GProcess` instance (inherits from `multiprocessing.Process`)
    """
    if not (isinstance(childhandles, list) or isinstance(childhandles, tuple)):
        childhandles = (childhandles,)
    if WINDOWS:
        for h in _all_handles:
            h._pre_createprocess_windows()
    p = GProcess(
        target=_child,
        name=name,
        args=(target, childhandles, _all_handles, kwargs))
    if daemon is not None:
        p.daemon = daemon
    p.start()
    if WINDOWS:
        for h in _all_handles:
            h._post_createprocess_windows()
    # Close file handlers in parent that are not further required.
    for h in childhandles:
        log.debug("Remove %s in parent." % h)
        h.close()
    return p


class GProcess(multiprocessing.Process):
    def join(self, timeout=None):
        """
        Wait cooperatively until child process terminates.

        On Unix, this calls waitpid() and therefore prevents zombie creation
        if applied properly.

        TODO:
            - We could install our own signal handler/watcher based on
              SIGCHLD (on Unix). Would be cleaner than frequent polling.
        """
        # `is_alive()` invokes `waitpid()` on Unix.
        with gevent.Timeout(timeout, False):
            while self.is_alive():
                gevent.sleep(0.1)
        # Call original method in non-blocking mode, even if timeout was
        # triggered above: clean up after child as designed by Process class.
        super(GProcess, self).join(timeout=0)


class GPipeError(Exception):
    pass


class _GPipeHandle(object):
    def __init__(self):
        self._id = os.urandom(3).encode("hex")
        self._legit_pid = os.getpid()
        self._make_nonblocking()
        self._glock = gevent.lock.Semaphore(value=1)
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
        self._validate()
        if not self._glock.acquire(blocking=False):
            raise GPipeError("GPipeHandle locked for I/O operation.")
        log.debug("Invalidating %s ..." % self)
        self._closed = True
        if self._fd is not None:
            log.debug("os.close(%s)" % self._fd)
            os.close(self._fd)
            self._fd = None
        if self in _all_handles:
            log.debug("Remove %s from _all_handles" % self)
            _all_handles.remove(self)
        self._glock.release()

    def _set_legit_process(self):
        log.debug("Legitimate %s" % self)
        self._legit_pid = os.getpid()

    def _validate(self):
        """Raise exception if this handle is not registered to be used in
        the current process.

        Intended to be called before every operation on `self._fd`.
        Reveals wrong usage of this module in the context of multiple
        processes. Might save the user the trouble of tedious debugging
        sessions. Based on `os.getpid()`, which uses a fast system call.
        Benchmarks show that this method does almost not affect the
        performance of the module. Profiling reveals that while
        `posix.read()` consumes e.g. 3.40 s of CPU time, this method
        consumes 0.12 s.

        In the future, we might decide to not call this method within
        each get and put operation performed on a pipe.
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
            self._fd = msvcrt.open_osfhandle(self._ihfd, self._descr_flag)
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
        self._descr_flag = os.O_RDONLY
        _GPipeHandle.__init__(self)

    def _recv_in_buffer(self, size):
        """Read `size` bytes cooperatively from file descriptor to buffer."""
        readbuf = io.BytesIO()
        remaining = size
        while remaining > 0:
            chunk = _READ_NB(self._fd, remaining)
            n = len(chunk)
            if n == 0:
                if remaining == size:
                    # Other pipe end was closed
                    raise EOFError("Other pipe end was closed.")
                else:
                    raise IOError("Message interrupted by EOF")
            readbuf.write(chunk)
            remaining -= n
        return readbuf

    def get(self):
        """Receive and return (un)picklelable object from pipe.

        Blocks cooperatively until message is available.
        TODO: timeout option"""
        self._validate()
        with self._glock:
            msize, = struct.unpack("!i", self._recv_in_buffer(4).getvalue())
            bindata = self._recv_in_buffer(msize).getvalue()
            return pickle.loads(bindata)


class _GPipeWriter(_GPipeHandle):
    def __init__(self, pipe_write_fd):
        self._fd = pipe_write_fd
        self._descr_flag = os.O_WRONLY
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
        """Put pickleable object into the pipe."""
        self._validate()
        with self._glock:
            bindata = pickle.dumps(o, pickle.HIGHEST_PROTOCOL)
            # TODO: one write instead of two?
            self._write(struct.pack("!i", len(bindata)))
            self._write(bindata)

