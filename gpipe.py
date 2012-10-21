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
from collections import deque
try:
    import simplejson as json
except ImportError:
    import json
import gevent.os


WINDOWS = sys.platform == "win32"
log = logging.getLogger()


def pipe():
    r, w = os.pipe()
    return _GPipeReader(r), _GPipeWriter(w)


class _GPipeHandler(object):
    def close(self):
        """Close pipe file descriptor."""
        os.close(self._fd)

    def pre_windows_process_inheritance(self):
        """Prepare file descriptor for transfer to subprocess on Windows. Call
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
        of the multiprocessing module in Python 2.6 up to the current develop-
        ment version of Python 3 (as of 2012-10-20).

        The code below is strongly influenced by multiprocessing/forking.py.
        """
        if not WINDOWS:
            return
        import msvcrt
        from multiprocessing.forking import duplicate
        # Get Windows file handle from C file descriptor.
        h = msvcrt.get_osfhandle(self._fd)
        # Duplicate file handle, rendering the duplicate inheritable by
        # processes created by the current process. Store duplicate.
        self._ih = duplicate(handle=h, inheritable=True)
        # Close and get rid of the "old" file descriptor.
        os.close(self._fd)
        self._fd = None

    def post_windows_process_inheritance(self):
        """Restore file descriptor after transfer to subprocess on Windows. Call
        in the newliy spawned process right after passing the reader/writer to
        a `multiprocessing.Process`.
        """
        if not WINDOWS:
            return
        import msvcrt            
        if self._fd is not None:
            raise Exception("First, call `pre_windows_process_inheritance`.")
        # Get C file descriptor from (iherited) Windows file handle, store it.    
        self._fd = msvcrt.open_osfhandle(self._ih, self._descr_flag)
        del self._ih


class _GPipeReader(_GPipeHandler):
    def __init__(self, pipe_read_fd):
        self._fd = pipe_read_fd   
        self._messages = deque()
        self._residual = ''
        self._descr_flag = os.O_RDONLY
        # TODO: Research reasonable buffer size. In preliminary benchmarks,
        # I've seen that a large buffer size (around 1M) greatly improves
        # performance for large messages and does not hurt for small 
        # messages.        
        self._readbuffer = 1000000

    def set_buffer(self, bufsize):
        """Set read buffer size of `os.read()` to `bufsize`.
        """
        self._readbuffer = bufsize
        
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
        """
        # Optimize parsing algorithm?
        # For large messages (> 100 kB) splitlines becomes quite expensive.
        # In _residual there is no newline, so it's stupid to include it.
        while not self._messages:
            lines = gevent.os.read(self._fd, self._readbuffer).splitlines(True)
            lines[0] = self._residual + lines[0]
            self._residual = ''
            if not lines[-1].endswith('\n'):
                self._residual = lines.pop()
            self._messages.extend(lines)
        if raw:
            return self._messages.popleft()
        # Encoded messages are still terminated with a newline character. The 
        # JSON decoder seems to ignore (remove) it.
        return json.loads(self._messages.popleft())


class _GPipeWriter(_GPipeHandler):
    def __init__(self, pipe_write_fd):
        self._fd = pipe_write_fd
        self._descr_flag = os.O_WRONLY

    def put(self, m, raw=False):
        """Put message into the pipe in a gevent-cooperative manner.

        By default, the message is JSON-encoded before written to the pipe.
        
        Args:
            `m`: JSON-encodable object
            `raw` (default: `False`): If `True`, do not JSON-encode message (Re-
                quires `m` to be a bytestring).
                
        Based on `gevent.os.write()`, a cooperative variant of `os.write()`.
        """    
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
            # are be handled by this loop.
            diff = len(m) - gevent.os.write(self._fd, m)
            if not diff:
                break
            m = m[-diff:]
