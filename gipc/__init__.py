# -*- coding: utf-8 -*-
# Copyright 2012-2013 Jan-Philip Gehrcke. See LICENSE file for details.


version_info = (0, 3, 0)
__version__ = ".".join(map(str, version_info))


from gipc import pipe, start_process, GIPCError, GIPCClosed, GIPCLocked
