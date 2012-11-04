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
 TODO:- handler encode/decode methods that are called by writer/
        reader. Facilitates implementation of other codecs in the
        future (e.g. pickle).
      - split pre/post fork methods and windows-specific modifications
      - properly deal with _validate_process (profile it and make it
        deactivatable

possibly in contradiction with the above:

      - yet better: add spawn_process_with_me method that wraps a call
        to Process(target, args, kwargs), executes gevent reinit in
        child and closes 2 unnecessary file handlers after forking
      - increase communication performance (increase bandwidth, decrease
        latency): implement binary communication protocol (look at
        multiprocessing Connections, make use of pickle,
        UNIX domain sockets, ...

Where we currently manage about 400 MB/s, lmbench on the same machine does:

[jang@pi:/usr/lib/lmbench/bin/x86_64-linux-gnu]
22:02:00 $ ./bw_unix
AF_UNIX sock stream bandwidth: 8343.00 MB/sec
[jang@pi:/usr/lib/lmbench/bin/x86_64-linux-gnu]
22:02:42 $ ./bw_pipe
Pipe bandwidth: 1523.87 MB/sec
"""

import os
import sys
import logging
import io
import struct
try:
   import cPickle as pickle
except:
   import pickle

from collections import deque
try:
    import simplejson as json
except ImportError:
    import json
import gevent.os
import gevent


WINDOWS = sys.platform == "win32"
log = logging.getLogger()


def pipe():
    # Windows (msdn.microsoft.com/en-us/library/windows/desktop/aa365152%28v=vs.85%29.aspx):
    #   - CreatePipe(&read, &write, NULL, 0)
    #   - Create an anonymous pipe, let system handle buffer size.
    #   - Anonymous pipes are implemented using a named pipe with a unique name.
    #   - Asynchronous (overlapped) read and write operations are not supported
    #     by anonymous pipes
    # Posix (http://linux.die.net/man/2/pipe):
    #   - pipe(fds)
    #   - on Linux, the pipe buffer usually is 4096 bytes
    r, w = os.pipe()
    return _GPipeReader(r), _GPipeWriter(w)


class _GPipeHandler(object):
    def __init__(self):
        self._legit_pid = os.getpid()

    def close(self):
        """Close pipe file descriptor."""
        self._validate_process()
        os.close(self._fd)

    def _validate_process(self):
        if os.getpid() != self._legit_pid:
            return
            raise RuntimeError(
                "GPipeHandler not registered for current process.")

    def pre_fork(self):
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
        # Force user to call `post_fork` after `pre_fork`: hide fd
        self._tempfd = self._fd
        self._fd = None
        if not WINDOWS:
            return
        import msvcrt
        from multiprocessing.forking import duplicate
        # Get Windows file handle from C file descriptor.
        h = msvcrt.get_osfhandle(self._tempfd)
        # Duplicate file handle, rendering the duplicate inheritable by
        # processes created by the current process. Store duplicate.
        self._ihfd = duplicate(handle=h, inheritable=True)
        # Close "old" (in-inheritable) file descriptor.
        os.close(self._tempfd)

    def post_fork(self):
        """
        """
        if self._fd is not None:
            raise RuntimeError(
                "`post_fork` called without prior call to `pre_fork`.")
        if WINDOWS:
            import msvcrt
            # Get C file descriptor from Windows file handle.
            self._tempfd = msvcrt.open_osfhandle(self._ihfd, self._descr_flag)
            del self._ihfd
        pid = os.getpid()
        if pid != self._legit_pid:
            # Child:
            # Restore file descriptor
            self._fd = self._tempfd
            del self._tempfd
            # Make child's PID the legit PID
            self._legit_pid = pid
            # Re-init the gevent event loop (get rid of events and greenlets
            # and events that have been registered/spawned before forking)
            gevent.reinit()
        else:
            # Parent: close file descriptor
            os.close(self._tempfd)


class _GPipeReader(_GPipeHandler):
    def __init__(self, pipe_read_fd):
        _GPipeHandler.__init__(self)
        self._fd = pipe_read_fd
        self._messages = deque()
        self._residual = []
        self._descr_flag = os.O_RDONLY
        # TODO: Research reasonable buffer size. POSIX pipes have a
        # capacity of 65536 bytes. Make buffer OS-dependent? On Windows,
        # for IPC, 65536 yields 2x performance as with 1000000.
        self._readbuffer = 65536

    def set_buffer(self, bufsize):
        """Set read buffer size of `os.read()` to `bufsize`.
        """
        self._readbuffer = bufsize

    def _recv_in_buffer(self, size):
        #log.debug("recv in buffer")
        readbuf = io.BytesIO()
        remaining = size
        while remaining > 0:
            chunk = gevent.os.read(self._fd, remaining)
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
        _GPipeHandler.__init__(self)
        self._fd = pipe_write_fd
        self._descr_flag = os.O_WRONLY

    def _write(self, bindata):
        while True:
            diff = len(bindata) - gevent.os.write(self._fd, bindata)
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
