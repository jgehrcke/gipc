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


def pipe(raw=False):
    r, w = os.pipe()
    return _GPipeReader(r, raw), _GPipeWriter(w, raw)


class _GPipeHandler(object):
    def close(self):
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
        There is no API officially exposed. However, the function
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
        right after passing the reader/writer to a `multiprocessing.Process`.
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
    def __init__(self, pipe_read_fd, raw=False):
        self._fd = pipe_read_fd
        self._raw = raw        
        self._messages = deque()
        self._residual = ''
        self._descr_flag = os.O_RDONLY

    def get(self):
        while not self._messages:
            # TODO: Research reasonable buffer size
            lines = (self._residual +
                gevent.os.read(self._fd, 99999)).splitlines(True)
            self._residual = ''
            if not lines[-1].endswith('\n'):
                self._residual = lines.pop()
            self._messages.extend(lines)
        if self._raw:
            return self._messages.popleft()
        # Each encoded msg has trailing \n. Could be removed with rstrip().
        # However, it looks like the JSON decoder does it.
        return json.loads(self._messages.popleft())


class _GPipeWriter(_GPipeHandler):
    def __init__(self, pipe_write_fd, raw=False):
        self._fd = pipe_write_fd
        self._raw = raw
        self._descr_flag = os.O_WRONLY

    def put(self, m):
        if not self._raw:
            m = json.dumps(m)+'\n' # Returns bytestring.
        # Else: user must make sure `m` is bytestring and delimit messages
        # himself via newline char.
        while True:
            # Occasionally, not all bytes are written at once.
            diff = len(m) - gevent.os.write(self._fd, m)
            if not diff:
                break
            m = m[-diff:]
