Version 0.3.0 (Feb 11, 2013)
----------------------------
    - Add bidirectional message transfer channels for IPC.
    - Prevent multiprocessing from swallowing SIGCHLD signals. Eliminates race
      condition between poll via os.waitpid() and libev child watchers.
    - Don't pass dispensable gipc handles to child.
    - Properly deal with handles that are locked for I/O operation while being
      inherited by child.
    - Various minor code changes, and a new class of unit tests for more complex
      scenarios.
    

Version 0.2.0 (Jan 31, 2013)
----------------------------
    - Remove gevent hub threadpool before destroying hub in child (makes gevent
      reset in child work more reliable).


Version 0.1.0 (Dec 12, 2012)
----------------------------
    - Initial release.
