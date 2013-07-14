Version 0.3.2 (July 14, 2013)
-----------------------------
    - Don't provide and use distribute_setup.py anymore. Thanks to Guy
      Rozendorn.
    - Slightly improve pipe write performance (measured improvement of up to
      10 % in data throughput as well as message transmission rate).


Version 0.3.1 (Apr 22, 2013)
----------------------------
    - Fix `issue #1 <https://bitbucket.org/jgehrcke/gipc/issue/1>`_: don't
      import gipc from setup.py anymore.
    - Fix: make GProcess' exitcode return ``None`` if ``Popen`` object still
      not existing.
    - Fix ``GProcess.is_alive``: Raise exception if process has not been
      started yet.
    - Create event object after forking instead of before (one reference to old
      Hub object less in child).
    - Make test classes newstyle. Doh.
    - Modify documentation theme.


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
