version_info = (0, 3, 0)
__version__ = ".".join(map(str, version_info))

from gipc import pipe, start_process, GIPCError, GIPCClosed, GIPCLocked
