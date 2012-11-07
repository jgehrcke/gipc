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


import os
import sys
import logging
import io
import struct
try:
   import cPickle as pickle
except:
   import pickle
import multiprocessing
WINDOWS = sys.platform == "win32"
if WINDOWS:
    import msvcrt
import gevent.os
import gevent


log = logging.getLogger()


# Define non-blocking read and write functions
if hasattr(gevent.os, 'nb_write'):
    # We're on a POSIX system and can use actual non-blocking I/O
    _READ_NB = gevent.os.nb_read
    _WRITE_NB = gevent.os.nb_write
else:
    # We're on Windows and fake non-blocking I/O based on a gevent threadpool
    _READ_NB = gevent.os.tp_read
    _WRITE_NB = gevent.os.tp_write


# Container for keeping track of valid `_GPipeHandler`s
_all_handles = []


def pipe():
    """Create pipe reader and writer.

    os.pipe() implementation on Windows:
      - based on CreatePipe(&read, &write, NULL, 0) (http://bit.ly/RDuKUm)
      - creates an anonymous pipe, lets system handle buffer size.
      - anonymous pipes are implemented using a named pipe with a unique name.
      - asynchronous (overlapped) read and write operations are not supported
        by anonymous pipes
    os.pipe() on POSIX (http://linux.die.net/man/2/pipe):
      - based on system call pipe(fds)
      - common Linux: pipe buffer is 4096 bytes, pipe capacity is 65536 bytes

    Returns:
        (reader, writer) tuple (both instances of `_GPipeHandler`).
    """
    r, w = os.pipe()
    reader = _GPipeReader(r)
    writer = _GPipeWriter(w)
    _all_handles.append(reader)
    _all_handles.append(writer)
    return reader, writer


def _subprocess(target, childhandles, kwargs):
    """Runs in child process. Fixes up situation in child process and executes
    user-given function.

    `target`: user-given function to be called with `kwargs`
    `childhandles`: GPipeHandlers that are intented to be used in child.
    """
    if not WINDOWS:
        # Clean up after fork.
        # Call `libev.ev_loop_fork()`: required after fork
        gevent.reinit()
        # Destroy default event loop via `libev.ev_loop_destroy()` and delete
        # hub. This gets rid of all registered events
        # and greenlets that have been duplicated from the parent.
        gevent.get_hub().destroy(destroy_loop=True)
        # Create a fresh event loop via `ev_loop_new` and a new hub.
        gevent.get_hub()
    else:
        # Restore file descriptors on Windows.
        for h in childhandles:
            h._post_fork_windows()
    # Close pipe ends in child that are not intended for further usage.
    for h in _all_handles:
        if not h in childhandles:
            h.close()
    target(*childhandles, **kwargs)


def start_process(childhandles, target, name=None, kwargs={}, daemon=None):
    """Spawn child process and execute target(*childhandles, **kwargs) there.

    Process creation is based on multiprocessing.Process(). When working with
    gevent and gevent-messagepipe, instead of calling Process() on your own,
    create child processes via this method. It takes care of
        - closing dispensable file descriptors after subprocess creation.
        - proper file descriptor inheritance on Windows.
        - re-initialization of the gevent event loop in the subprocess (no
          greenlet spawned in the parent will run in the child).

    Args:
        `childhandles`: GPipeHandler or list or tuple of GPipeHandlers
            that are intented to be used in the child. Will be unusable in
            parent afterwards.
        `target`: user-given function to be called with `kwargs`
        `name`: forwarded to multiprocessing.Process()
        `daemon`: flag that is set before starting process
        `kwargs`: dictionary defining keyword arguments provided to `target`

    Returns:
        `multiprocessing.Process` instance

    """
    if not (isinstance(childhandles, list) or isinstance(childhandles, tuple)):
        childhandles = (childhandles,)
    for h in childhandles:
        h._pre_fork_windows()
    p = GProcess(
        target=_subprocess,
        name=name,
        args=(target, childhandles, kwargs))
    if daemon is not None:
        p.daemon = daemon
    p.start()
    # Close file handlers in parent that are not further required.
    for h in childhandles:
        h.close()
    return p


class GProcess(multiprocessing.Process):
    def join(self, timeout=None):
        """
        Wait cooperatively until child process terminates.

        On Unix, this calls waitpid() and therefore prevents zombie creation
        if applied properly. Currently based on polling with a certain rate.

        TODO:   - implement timeout based on gevent timeouts
                - we could install our own signal handler/watcher based on
                  SIGCHLD. at least on Unix, this could be much cleaner than
                  frequent polling.
        """
        # `is_alive()` invokes `waitpid()` on Unix.
        with gevent.Timeout(timeout, False):
            while self.is_alive():
                gevent.sleep(0.1)
        # Call original method in any case (if child is dead, clean up
        # after it as designed by Process class).
        super(GProcess, self).join(timeout=0)


class _GPipeHandler(object):
    def __init__(self):
        #self._legit_pid = os.getpid()
        self._make_nonblocking()

    def _make_nonblocking(self):
        if hasattr(gevent.os, 'make_nonblocking'):
            # On POSIX, file descriptor flags are inherited after forking,
            # i.e. it is enough to make them nonblocking once (in parent).
            gevent.os.make_nonblocking(self._fd)

    def close(self):
        """Close pipe handler

        Closes underlying file descriptor and removes the handler from the
        list of valid handlers.
        """
        if self._fd is not None:
            log.debug("Close fd %s in process %s" % (self._fd, os.getpid()))
            os.close(self._fd)
        if self in _all_handles:
            _all_handles.remove(self)

    def _validate_process(self):
        if os.getpid() != self._legit_pid:
            return
            raise RuntimeError(
                "GPipeHandler not registered for current process.")

    def _pre_fork_windows(self):
        """Prepare file descriptor for transfer to child process on Windows.

        By default, file descriptors are not inherited by subprocesses on
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
            self._fd = None

    def _post_fork_windows(self):
        """Restore file descriptor in child on Windows."""
        if WINDOWS:
            # Get C file descriptor from Windows file handle.
            self._fd = msvcrt.open_osfhandle(self._ihfd, self._descr_flag)
            del self._ihfd


class _GPipeReader(_GPipeHandler):
    def __init__(self, pipe_read_fd):
        self._fd = pipe_read_fd
        self._descr_flag = os.O_RDONLY
        _GPipeHandler.__init__(self)

    def _recv_in_buffer(self, size):
        """Read `size` bytes cooperatively from file descriptor to buffer."""
        readbuf = io.BytesIO()
        remaining = size
        while remaining > 0:
            chunk = _READ_NB(self._fd, remaining)
            n = len(chunk)
            if n == 0:
                if remaining == size:
                    raise EOFError
                else:
                    raise IOError("Message interrupted by EOF")
            readbuf.write(chunk)
            remaining -= n
        return readbuf

    def get(self):
        """Receive and return (un)picklelable object from pipe.

        Blocks cooperatively until message is available.
        TODO: timeout option"""
        #self._validate_process()
        messagesize, = struct.unpack("!i", self._recv_in_buffer(4).getvalue())
        return pickle.loads(self._recv_in_buffer(messagesize).getvalue())

    def __str__(self):
        return "<_GPipeReader fd: %s>" % (self._fd)


class _GPipeWriter(_GPipeHandler):
    def __init__(self, pipe_write_fd):
        self._fd = pipe_write_fd
        self._descr_flag = os.O_WRONLY
        _GPipeHandler.__init__(self)

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
        #self._validate_process()
        bindata = pickle.dumps(o, pickle.HIGHEST_PROTOCOL)
        # TODO: one write instead of two?
        self._write(struct.pack("!i", len(bindata)))
        self._write(bindata)

    def __str__(self):
        return "<_GPipeWriter fd: %s>" % (self._fd)

