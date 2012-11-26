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


# helpful sources:
# https://github.com/ioLab/python-ioLabs/blob/master/hid/win32.py
# https://bitbucket.org/pchambon/python-rock-solid-tools/


import ctypes
from ctypes import wintypes
from ctypes.wintypes import DWORD
from ctypes.wintypes import BOOL
from ctypes.wintypes import HANDLE
from ctypes.wintypes import LARGE_INTEGER
from ctypes.wintypes import LPCVOID
from ctypes.wintypes import LPVOID
from ctypes.wintypes import LONG
from ctypes.wintypes import LPCSTR
from ctypes.wintypes import LPCWSTR
from ctypes.wintypes import _FILETIME
from ctypes.wintypes import FILETIME
win32 = ctypes.windll.kernel32


LPDWORD = ctypes.POINTER(DWORD)
LPCTSTR = ctypes.c_wchar_p

NULL = LPDWORD()


class _OVERLAPPED(ctypes.Structure):
    pass


class _inner_struct(ctypes.Structure):
    _fields_ = [('Offset', wintypes.DWORD),
                ('OffsetHigh', wintypes.DWORD),
               ]

class _inner_union(ctypes.Union):
    _fields_  = [('anon_struct', _inner_struct), # struct
                 ('Pointer', ctypes.c_void_p), # PVOID
                ]

class OVERLAPPED(ctypes.Structure):
    _fields_ = [('Internal', ctypes.c_void_p), # ULONG_PTR
                ('InternalHigh', ctypes.c_void_p), # ULONG_PTR
                ('_inner_union', _inner_union),
                ('hEvent', ctypes.c_void_p), # HANDLE
               ]


OVERLAPPED = _OVERLAPPED
LPOVERLAPPED = ctypes.POINTER(_OVERLAPPED)
LPOVERLAPPED_COMPLETION_ROUTINE = ctypes.WINFUNCTYPE(None, DWORD, DWORD, LPOVERLAPPED)


class _SECURITY_ATTRIBUTES(ctypes.Structure):
    pass
SECURITY_ATTRIBUTES = _SECURITY_ATTRIBUTES
LPSECURITY_ATTRIBUTES = ctypes.POINTER(_SECURITY_ATTRIBUTES)

GetLastError = win32.GetLastError
GetLastError.restype = DWORD
GetLastError.argtypes = []

CreateNamedPipe = win32.CreateNamedPipeW
CreateNamedPipe.restype = HANDLE
CreateNamedPipe.argtypes = [
    LPCSTR, DWORD, DWORD, DWORD, DWORD, DWORD, DWORD, LPSECURITY_ATTRIBUTES]

ConnectNamedPipe = win32.ConnectNamedPipe
ConnectNamedPipe.restype = BOOL
ConnectNamedPipe.argtypes = [HANDLE, LPOVERLAPPED]

SetNamedPipeHandleState = win32.SetNamedPipeHandleState
SetNamedPipeHandleState.restype = BOOL
SetNamedPipeHandleState.argtypes = [HANDLE, LPDWORD, LPDWORD, LPDWORD]

CloseHandle = win32.CloseHandle
CloseHandle.restype = HANDLE
CloseHandle.argtypes = [HANDLE]

CreateFile = win32.CreateFileW
CreateFile.restype = HANDLE
CreateFile.argtypes = [
    LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE]

GetOverlappedResult = win32.GetOverlappedResult
GetOverlappedResult.restype = BOOL
GetOverlappedResult.argtypes = [
    HANDLE, LPOVERLAPPED, LPDWORD, BOOL]

WriteFileEx = win32.WriteFileEx
WriteFileEx.restype = BOOL
WriteFileEx.argtypes = [
    HANDLE, LPCVOID, DWORD, LPOVERLAPPED, LPOVERLAPPED_COMPLETION_ROUTINE]

ReadFileEx = win32.ReadFileEx
ReadFileEx.argtypes = [
    HANDLE, LPVOID, DWORD, LPOVERLAPPED, LPOVERLAPPED_COMPLETION_ROUTINE]




'''
The Windows (Win32) HID interface module.
Dynamically loaded on Windows platforms.
Refer to the hid module for available functions
'''


#http://permalink.gmane.org/gmane.comp.python.ctypes/2410



def GetLastErrorMessage():
    error = Kernel32.GetLastError()
    Kernel32.SetLastError(0)
    msg = c_char_p()

    Kernel32.FormatMessageA(
        FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_IGNORE_INSERTS,
        None,error,0,byref(msg), 0, None)
    s = 'Windows error #%d: %s' % (error, msg.value)
    Kernel32.LocalFree(msg)
    return s

# All pipe-related constants
# from https://bitbucket.org/pchambon/python-rock-solid-tools/
PIPE_CLIENT_END = 0 # Variable c_int '0'
PIPE_WAIT = 0 # Variable c_int '0'
RPC_X_PIPE_EMPTY = 1918 # Variable c_long '1918l'
PIPE_TYPE_BYTE = 0 # Variable c_int '0'
ERROR_PIPE_BUSY = 231 # Variable c_long '231l'
RPC_X_INVALID_PIPE_OBJECT = 1830 # Variable c_long '1830l'
ERROR_BROKEN_PIPE = 109 # Variable c_long '109l'
PIPE_ACCESS_INBOUND = 1 # Variable c_int '1'
PIPE_TYPE_MESSAGE = 4 # Variable c_int '4'
FILE_FLAG_FIRST_PIPE_INSTANCE = 524288 # Variable c_int '524288'
RPC_X_WRONG_PIPE_ORDER = 1831 # Variable c_long '1831l'
ERROR_PIPE_NOT_CONNECTED = 233 # Variable c_long '233l'
RPC_INTERFACE_HAS_PIPES = 1 # Variable c_int '1'
PIPE_SERVER_END = 1 # Variable c_int '1'
FILE_CREATE_PIPE_INSTANCE = 4 # Variable c_int '4'
FILE_DEVICE_NAMED_PIPE = 17 # Variable c_int '17'
FILE_TYPE_PIPE = 3 # Variable c_int '3'
PIPE_NOWAIT = 1 # Variable c_int '1'
PIPE_REJECT_REMOTE_CLIENTS = 8 # Variable c_int '8'
RPC_X_WRONG_PIPE_VERSION = 1832 # Variable c_long '1832l'
ERROR_PIPE_CONNECTED = 535 # Variable c_long '535l'
PIPE_READMODE_MESSAGE = 2 # Variable c_int '2'
PIPE_READMODE_MESSAGE_REF = ctypes.byref(ctypes.wintypes.DWORD(PIPE_READMODE_MESSAGE))


PIPE_UNLIMITED_INSTANCES = 255 # Variable c_int '255'
PIPE_ACCESS_DUPLEX = 3 # Variable c_int '3'
ERROR_PIPE_LOCAL = 229 # Variable c_long '229l'
ERROR_PIPE_LISTENING = 536 # Variable c_long '536l'
PIPE_ACCEPT_REMOTE_CLIENTS = 0 # Variable c_int '0'
ERROR_BAD_PIPE = 230 # Variable c_long '230l'
PIPE_ACCESS_OUTBOUND = 2 # Variable c_int '2'
RPC_X_PIPE_CLOSED = 1916 # Variable c_long '1916l'
PIPE_READMODE_BYTE = 0 # Variable c_int '0'

# File-related constants
GENERIC_READ = 2147483648L # Variable c_ulong '-2147483648ul'
GENERIC_WRITE = 1073741824
FILE_FLAG_WRITE_THROUGH = 2147483648L # Variable c_uint '-2147483648u'
FILE_FLAG_DELETE_ON_CLOSE = 67108864 # Variable c_int '67108864'
FILE_FLAG_OVERLAPPED = 1073741824 # Variable c_int '1073741824'
FILE_FLAG_FIRST_PIPE_INSTANCE = 524288 # Variable c_int '524288'
FILE_FLAG_SEQUENTIAL_SCAN = 134217728 # Variable c_int '134217728'
FILE_FLAG_POSIX_SEMANTICS = 16777216 # Variable c_int '16777216'
FILE_FLAG_OPEN_NO_RECALL = 1048576 # Variable c_int '1048576'
FILE_FLAG_RANDOM_ACCESS = 268435456 # Variable c_int '268435456'
FILE_FLAG_BACKUP_SEMANTICS = 33554432 # Variable c_int '33554432'
FILE_FLAG_OPEN_REPARSE_POINT = 2097152 # Variable c_int '2097152'
FILE_FLAG_NO_BUFFERING = 536870912 # Variable c_int '536870912'
OPEN_EXISTING = 3 # Variable c_int '3'


NMPWAIT_USE_DEFAULT_WAIT = 0 # Variable c_int '0'
NMPWAIT_WAIT_FOREVER = 4294967295L # Variable c_uint '-1u'
NMPWAIT_NOWAIT = 1 # Variable c_int '1'


WAIT_ABANDONED = 128L # Variable c_ulong '128ul'
WAIT_OBJECT_0 = 0L # Variable c_ulong '0ul'
WAIT_FAILED = 4294967295L # Variable c_ulong '-1u'
WAIT_TIMEOUT = 258 # Variable c_long '258l'



