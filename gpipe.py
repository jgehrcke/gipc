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
"""

import os
import sys
import logging
import io
import struct
from multiprocessing import Process
try:
   import cPickle as pickle
except:
   import pickle
WINDOWS = sys.platform == "win32"
if WINDOWS:
    import msvcrt
from collections import deque
try:
    import simplejson as json
except ImportError:
    import json
import gevent.os
import gevent

log = logging.getLogger()

# Define non-blocking read and write functions
if hasattr(gevent.os, 'nb_write'):
    # Usually POSIX (actual non-blocking I/O)
    _READ = gevent.os.nb_read
    _WRITE = gevent.os.nb_write
else:
    # Usually Windows (fake non-blocking I/O based on threadpool)
    _READ = gevent.os.tb_read
    _WRITE = gevent.os.tb_write


_all_handles = []


def pipe():
    # on Windows (msdn.microsoft.com/en-us/library/windows/desktop/aa365152%28v=vs.85%29.aspx):
    #   - based on CreatePipe(&read, &write, NULL, 0)
    #   - creates an anonymous pipe, lets system handle buffer size.
    #   - anonymous pipes are implemented using a named pipe with a unique name.
    #   - asynchronous (overlapped) read and write operations are not supported
    #     by anonymous pipes
    # POSIX (http://linux.die.net/man/2/pipe):
    #   - based on system call pipe(fds)
    #   - on Linux, the pipe buffer usually is 4096 bytes
    r, w = os.pipe()
    reader = _GPipeReader(r)
    writer = _GPipeWriter(w)
    _all_handles.append(reader)
    _all_handles.append(writer)
    return reader, writer


def _subprocess(target, childhandles, kwargs):
    # Re-init the gevent event loop (get rid of events and greenlets
    # that have been registered/spawned before forking)
    gevent.reinit()
    h = gevent.get_hub()
    #h.loop.destroy()
    #h.loop.__init__()
    print repr(h)
    for h in childhandles:
        h.post_fork_windows()
    # Close file handlers (pipe ends) in child that are not intended for
    # further usage.
    for h in _all_handles:
        if not h in childhandles:
            h.close()
    target(*childhandles, **kwargs)


def start_process(childhandles, target, name=None, kwargs={}, daemon=None):
    if not (isinstance(childhandles, list) or isinstance(childhandles, tuple)):
        childhandles = (childhandles,)
    for h in childhandles:
        h.pre_fork_windows()
    p = Process(
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


class _GPipeHandler(object):
    def __init__(self):
        self._legit_pid = os.getpid()
        self._make_nonblocking()

    def _make_nonblocking(self):
        if hasattr(gevent.os, 'make_nonblocking'):
            # On POSIX, file descriptor flags are inherited after forking,
            # i.e. it is enough to make nonblocking once.
            gevent.os.make_nonblocking(self._fd)

    def close(self):
        """Close pipe file descriptor."""
        #self._validate_process()
        if self in _all_handles:
            log.debug("Close fd %s in process %s" % (self._fd, os.getpid()))
            os.close(self._fd)
            _all_handles.remove(self)

    def _validate_process(self):
        if os.getpid() != self._legit_pid:
            return
            raise RuntimeError(
                "GPipeHandler not registered for current process.")

    def pre_fork_windows(self):
        """Prepare file descriptor for transfer to subprocess. Call
        right before passing the reader/writer to a `multiprocessing.Process`.

        By default, file descriptors are not inherited by subprocesses on
        Windows. However, they can be made inheritable via calling the system
        function `DuplicateHandle` while setting `bInheritHandle` to True. From
        MSDN:
            bInheritHandle:
                A variable that indicates whether the handle is inheritable.
                If TRUE, the duplicate handle can be inherited by new processes
                created by the target process. If FALSE, the new handle cannot
                be inherited.
        The Python `subprocess` and `multiprocessing` modules make use of this.
        There is no Python API officially exposed. However, the function
        `multiprocessing.forking.duplicate` is available since the introduction
        of the multiprocessing module in Python 2.6 up to the development
        version of Python 3 as of 2012-10-20. The code below is influenced by
        multiprocessing's forking.py.
        """
        if WINDOWS:
            from multiprocessing.forking import duplicate
            # Get Windows file handle from C file descriptor.
            h = msvcrt.get_osfhandle(self._fd)
            # Duplicate file handle, rendering the duplicate inheritable by
            # processes created by the current process. Store duplicate.
            self._ihfd = duplicate(handle=h, inheritable=True)
            # Close "old" (in-inheritable) file descriptor.
            os.close(self._fd)

    def post_fork_windows(self):
        """
        """
        if WINDOWS:
            # Get C file descriptor from Windows file handle.
            self._fd = msvcrt.open_osfhandle(self._ihfd, self._descr_flag)
            del self._ihfd


class _GPipeReader(_GPipeHandler):
    def __init__(self, pipe_read_fd):
        self._fd = pipe_read_fd
        self._messages = deque()
        self._residual = []
        self._descr_flag = os.O_RDONLY
        # TODO: Research reasonable buffer size. POSIX pipes have a
        # capacity of 65536 bytes. Make buffer OS-dependent? On Windows,
        # for IPC, 65536 yields 2x performance as with 1000000.
        self._readbuffer = 65536
        _GPipeHandler.__init__(self)

    def set_buffer(self, bufsize):
        """Set read buffer size of `os.read()` to `bufsize`.
        """
        self._readbuffer = bufsize

    def _recv_in_buffer(self, size):
        #log.debug("recv in buffer")
        readbuf = io.BytesIO()
        remaining = size
        while remaining > 0:
            chunk = _READ(self._fd, remaining)
            n = len(chunk)
            if n == 0:
                if remaining == size:
                    raise EOFError
                else:
                    raise IOError("Message interrupted by EOF")
            readbuf.write(chunk)
            remaining -= n
        #log.debug("read object!")
        return readbuf

    def pickleget(self):
        messagesize,  = struct.unpack("!i", self._recv_in_buffer(4).getvalue())
        return pickle.loads(self._recv_in_buffer(messagesize).getvalue())

    def get(self, raw=False):
        """Get next message. If not available, wait in a gevent-cooperative
        manner.

        By default, the message is JSON-decoded before returned.

        Args:
            `raw` (default: `False`): If `True`, do not JSON-decode message.

        Returns:
            - case `raw==False`: JSON-decoded message
            - case `raw==False`: message as bytestring

        Based on `gevent.os.read()`, a cooperative variant of `os.read()`.
        Message re-assembly method is profiled, optimized, and works well
        also for small buffer sizes.
        """
        #self._validate_process()
        while not self._messages:
            data = gevent.os.read(self._fd, self._readbuffer).splitlines(True)
            nlend = data[-1].endswith('\n')
            if self._residual and (nlend or len(data) > 1):
                data[0] = ''.join(self._residual+[data[0]])
                self._residual = []
            if not nlend:
                self._residual.append(data.pop())
            self._messages.extend(data)
        if raw:
            return self._messages.popleft()
        # Encoded messages are still terminated with a newline character. The
        # JSON decoder seems to ignore (remove) it.
        return json.loads(self._messages.popleft())

    def __str__(self):
        return "_GPipeReader"


class _GPipeWriter(_GPipeHandler):
    def __init__(self, pipe_write_fd):
        self._fd = pipe_write_fd
        self._descr_flag = os.O_WRONLY
        _GPipeHandler.__init__(self)

    def _write(self, bindata):
        while True:
            diff = len(bindata) - _WRITE(self._fd, bindata)
            if not diff:
                break
            bindata = bindata[-diff:]

    def pickleput(self, o):
        bindata = pickle.dumps(o, pickle.HIGHEST_PROTOCOL)
        self._write(struct.pack("!i", len(bindata)))
        self._write(bindata)

    def put(self, m, raw=False):
        """Put message into the pipe in a gevent-cooperative manner.

        By default, the message is JSON-encoded before written to the pipe.

        Args:
            `m`: JSON-encodable object
            `raw` (default: `False`): If `True`, do not JSON-encode message (Re-
                quires `m` to be a bytestring).

        Based on `gevent.os.write()`, a cooperative variant of `os.write()`.
        """
        #self._validate_process()
        if not raw:
            m = json.dumps(m)+'\n' # Returns bytestring.
        # Else: user must make sure `m` is bytestring and delimit messages
        # himself via newline char.
        while True:
            # http://linux.die.net/man/7/pipe:
            #  - Since Linux 2.6.11, the pipe capacity is 65536 bytes
            #  - Relevant for large messages:
            #    case O_NONBLOCK enabled, n > PIPE_BUF (4096 Byte, usually):
            #    """If the pipe is full, then write(2) fails, with errno set
            #    to EAGAIN. Otherwise, from 1 to n bytes may be written (i.e.,
            #    a "partial write" may occur; the caller should check the
            #    return value from write(2) to see how many bytes were
            #    actualy written), and these bytes may be interleaved with
            #    writes by other processes. """
            #
            # EAGAIN is handled within gevent.os.posix_write; partial writes
            # are handled by this loop.
            diff = len(m) - gevent.os.write(self._fd, m)
            if not diff:
                break
            m = m[-diff:]

    def __str__(self):
        return "_GPipeWriter"
