version_info = (0, 2, 0)
__version__ = ".".join(map(str, version_info))

from gipc import pipe, start_process, GIPCError, GIPCClosed, GIPCLocked, get_all_handles, set_all_handles
