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
import itertools
import tempfile
import sys

import gevent

import logging
logging.basicConfig(
  format='%(asctime)s,%(msecs)-6.1f [%(process)-5d]%(funcName)s# %(message)s',
  datefmt='%H:%M:%S')
log = logging.getLogger()
log.setLevel(logging.DEBUG)


#import win32api
#import win32pipe
#import win32file
#import win32event
#import winerror
#win32file.FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000

#_winapi = win32api
#_winapi.__dict__.update(win32pipe.__dict__)
#del win32pipe
#_winapi.__dict__.update(win32file.__dict__)
#del win32file

#import win32security


#import win_io_ex_functions
import win

def main():
    r, w = pipe()
    w.send_bytes('a'*99999)


def pipe(duplex=False):
    '''
Returns pair of connection objects at either end of a pipe
'''
    address = arbitrary_address('AF_PIPE')
    if duplex:
        openmode = win.PIPE_ACCESS_DUPLEX
        access = win.GENERIC_READ | win.GENERIC_WRITE
        obsize, ibsize = BUFSIZE, BUFSIZE
    else:
        openmode = win.PIPE_ACCESS_INBOUND
        access = win.GENERIC_WRITE
        obsize, ibsize = 0, BUFSIZE

    handle1 = win.CreateNamedPipe(
        address, openmode | win.FILE_FLAG_OVERLAPPED |
        win.FILE_FLAG_FIRST_PIPE_INSTANCE,
        win.PIPE_TYPE_MESSAGE | win.PIPE_READMODE_MESSAGE |
        win.PIPE_WAIT,
        1, obsize, ibsize, win.NMPWAIT_WAIT_FOREVER, win.SECURITY_ATTRIBUTES())

    ov = win.OVERLAPPED()
    # Wait for client to connect (async).
    r = win.ConnectNamedPipe(handle1, win.ctypes.byref(ov))
    # `r` might contain error codes.

    # Connect client.
    log.debug("connect client..")
    handle2 = win.CreateFile(
        address, access, 0, win.SECURITY_ATTRIBUTES(),
        win.OPEN_EXISTING,
        win.FILE_FLAG_OVERLAPPED, 0)

    win.SetNamedPipeHandleState(
        handle2, win.PIPE_READMODE_MESSAGE_REF, win.NULL, win.NULL)
    log.debug("Have set new read mode..")

    # Wait for client-connect-event (blocking)
    transferred = win.DWORD()
    r = win.GetOverlappedResult(handle1, win.ctypes.byref(ov), win.ctypes.byref(transferred), True)
    # pywin32 docs and MSDN are contradictionary regarding `r`.
    log.debug("transferred: %s" % transferred)

    sys.exit()

    c1 = PipeConnection(h1, writable=duplex)
    c2 = PipeConnection(h2, readable=duplex)

    return c1, c2


def arbitrary_address(family):
    '''
Return an arbitrary free address for the given family
'''
    if family == 'AF_INET':
        return ('localhost', 0)
    elif family == 'AF_UNIX':
        return tempfile.mktemp(prefix='listener-', dir=get_temp_dir())
    elif family == 'AF_PIPE':
        return tempfile.mktemp(prefix=r'\\.\pipe\pyc-%d-%d-' %
                               (os.getpid(), next(_mmap_counter)))
    else:
        raise ValueError('unrecognized family')


_mmap_counter = itertools.count()
BUFSIZE = 8192
# A very generous timeout when it comes to local connections...
CONNECTION_TIMEOUT = 20.


class _ConnectionBase:
    _handle = None

    def __init__(self, handle, readable=True, writable=True):
        #handle = handle.__index__()
        #if handle < 0:
            #raise ValueError("invalid handle")
        #if not readable and not writable:
            #raise ValueError(
                #"at least one of `readable` and `writable` must be True")
        self._handle = handle
        self._readable = readable
        self._writable = writable

    # XXX should we use util.Finalize instead of a __del__?

    def __del__(self):
        if self._handle is not None:
            self._close()

    def _check_closed(self):
        if self._handle is None:
            raise IOError("handle is closed")

    def _check_readable(self):
        if not self._readable:
            raise IOError("connection is write-only")

    def _check_writable(self):
        if not self._writable:
            raise IOError("connection is read-only")

    def _bad_message_length(self):
        if self._writable:
            self._readable = False
        else:
            self.close()
        raise IOError("bad message length")

    @property
    def closed(self):
        """True if the connection is closed"""
        return self._handle is None

    @property
    def readable(self):
        """True if the connection is readable"""
        return self._readable

    @property
    def writable(self):
        """True if the connection is writable"""
        return self._writable

    def fileno(self):
        """File descriptor or handle of the connection"""
        self._check_closed()
        return self._handle

    def close(self):
        """Close the connection"""
        if self._handle is not None:
            try:
                self._close()
            finally:
                self._handle = None

    def send_bytes(self, buf, offset=0, size=None):
        """Send the bytes data from a bytes-like object"""
        self._check_closed()
        self._check_writable()
        m = memoryview(buf)
        # HACK for byte-indexing of non-bytewise buffers (e.g. array.array)
        if m.itemsize > 1:
            m = memoryview(bytes(m))
        n = len(m)
        if offset < 0:
            raise ValueError("offset is negative")
        if n < offset:
            raise ValueError("buffer length < offset")
        if size is None:
            size = n - offset
        elif size < 0:
            raise ValueError("size is negative")
        elif offset + size > n:
            raise ValueError("buffer length < offset + size")
        self._send_bytes(m[offset:offset + size])

    def send(self, obj):
        """Send a (picklable) object"""
        self._check_closed()
        self._check_writable()
        buf = io.BytesIO()
        ForkingPickler(buf, pickle.HIGHEST_PROTOCOL).dump(obj)
        self._send_bytes(buf.getbuffer())

    def recv_bytes(self, maxlength=None):
        """
Receive bytes data as a bytes object.
"""
        self._check_closed()
        self._check_readable()
        if maxlength is not None and maxlength < 0:
            raise ValueError("negative maxlength")
        buf = self._recv_bytes(maxlength)
        if buf is None:
            self._bad_message_length()
        return buf.getvalue()

    def recv_bytes_into(self, buf, offset=0):
        """
Receive bytes data into a writeable buffer-like object.
Return the number of bytes read.
"""
        self._check_closed()
        self._check_readable()
        with memoryview(buf) as m:
            # Get bytesize of arbitrary buffer
            itemsize = m.itemsize
            bytesize = itemsize * len(m)
            if offset < 0:
                raise ValueError("negative offset")
            elif offset > bytesize:
                raise ValueError("offset too large")
            result = self._recv_bytes()
            size = result.tell()
            if bytesize < offset + size:
                raise BufferTooShort(result.getvalue())
            # Message can fit in dest
            result.seek(0)
            result.readinto(m[offset // itemsize :
                              (offset + size) // itemsize])
            return size

    def recv(self):
        """Receive a (picklable) object"""
        self._check_closed()
        self._check_readable()
        buf = self._recv_bytes()
        return pickle.loads(buf.getbuffer())

    def poll(self, timeout=0.0):
        """Whether there is any input available to be read"""
        self._check_closed()
        self._check_readable()
        return self._poll(timeout)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


class PipeConnection(_ConnectionBase):
    """
Connection class based on a Windows named pipe.
Overlapped I/O is used, so the handles must have been created
with FILE_FLAG_OVERLAPPED.
"""
    _got_empty_message = False

    def _close(self, _CloseHandle=win.CloseHandle):
        _CloseHandle(self._handle)

    def _send_bytes(self, buf):
        buf = buf.tobytes()

        def write_completion_callback(
                dwErrorCode, dwNumberOfBytesTransfered, lpOverlapped):
            log.debug('')

        overlap_completion=win_io_ex_functions.LPOVERLAPPED_COMPLETION_ROUTINE(
            write_completion_callback)

        overlapped = win_io_ex_functions.OVERLAPPED()

        result = win_io_ex_functions.WriteFileEx(
            self._handle,
            buf,
            len(buf),
            overlapped,
            overlap_completion)

        if not result:
            raise RuntimeError("WriteFileEx failed")

        sys.exit(1)



        ov = win32file.OVERLAPPED()
        err, nwritten = win32file.WriteFile(self._handle, buf.tobytes(), ov)
        # After this, `nwritten can't make sense`.
        log.debug('err: %s, nwritten: %s' % (err, nwritten))
        try:
            if err == winerror.ERROR_IO_PENDING:
                log.debug('Write dispatched, pending.')
                waitres = win32api.WaitForSingleObject(
                    ov.hEvent, win32event.INFINITE)
                assert waitres == WAIT_OBJECT_0
        except:
            #ov.cancel()
            raise
        finally:
            nwritten = win32pipe.GetOverlappedResult(
                self._handle, ov , True)
            #nwritten, err = ov.GetOverlappedResult(True)
        assert err == 0
        assert nwritten == len(buf)

    def _recv_bytes(self, maxsize=None):
        if self._got_empty_message:
            self._got_empty_message = False
            return io.BytesIO()
        else:
            bsize = 128 if maxsize is None else min(maxsize, 128)
            try:
                ov, err = win32file.ReadFile(self._handle, bsize,
                                            overlapped=True)
                try:
                    if err == _winapi.ERROR_IO_PENDING:
                        waitres = _winapi.WaitForMultipleObjects(
                            [ov.event], False, INFINITE)
                        assert waitres == WAIT_OBJECT_0
                except:
                    ov.cancel()
                    raise
                finally:
                    nread, err = ov.GetOverlappedResult(True)
                    if err == 0:
                        f = io.BytesIO()
                        f.write(ov.getbuffer())
                        return f
                    elif err == _winapi.ERROR_MORE_DATA:
                        return self._get_more_data(ov, maxsize)
            except IOError as e:
                if e.winerror == _winapi.ERROR_BROKEN_PIPE:
                    raise EOFError
                else:
                    raise
        raise RuntimeError("shouldn't get here; expected KeyboardInterrupt")

    def _poll(self, timeout):
        if (self._got_empty_message or
                    win32pipe.PeekNamedPipe(self._handle)[0] != 0):
            return True
        return bool(wait([self], timeout))

    def _get_more_data(self, ov, maxsize):
        buf = ov.getbuffer()
        f = io.BytesIO()
        f.write(buf)
        left = win32pipe.PeekNamedPipe(self._handle)[1]
        assert left > 0
        if maxsize is not None and len(buf) + left > maxsize:
            self._bad_message_length()
        ov, err = win32file.ReadFile(self._handle, left, overlapped=True)
        rbytes, err = ov.GetOverlappedResult(True)
        assert err == 0
        assert rbytes == left
        f.write(ov.getbuffer())
        return f

if __name__ == "__main__":
    main()
