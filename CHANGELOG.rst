Version 0.7.0 (in development)
------------------------------

    Breaking changes:

    - Require gevent 1.2.x.

    New platform support:

    - Add support for PyPy on Linux. Thanks to Oliver Margetts and to Heungsub
      Lee.

    Test / CI changes:

    - Do not test on CPython 3.3 anymore, but test on 3.5 and 3.6.
    - Test on PyPy2.7 and PyPy3.
    - Fix WSGI-related test, stabilize ``test_exitcode_previous_to_join``.


Version 0.6.0 (Jul 22, 2015)
----------------------------
    - Add support for CPython 3.3 and 3.4.
    - Require gevent >= 1.1b1.


Version 0.5.0 (Oct 22, 2014)
----------------------------
    - Improve large message throughput on Linux (see issue #13).
    - Work around read(2) system call flaw on Mac OS X (see issue #13).
    - Work around signal.NSIG-related problem on FreeBSD (see issue #10).
    - Do not alter SIGPIPE action during child bootstrap (breaking change,
      see issue #12).


Version 0.4.0 (Dec 07, 2013)
----------------------------
    - Implement data (de)serialization pipe API (allowing for raw byte
      transmission and for custom encoders/decoders).
    - Restore default signal disposition in child wrapper for all signals (see
      `issue #7 <https://bitbucket.org/jgehrcke/gipc/issue/7>`_).
    - Fix DeprecationWarning related to _PairContext class (see
      `issue #5 <https://bitbucket.org/jgehrcke/gipc/issue/5>`_).
    - Significantly improve large message write performance by using Python's
      buffer interface.
    - Require gevent 1.0 final release version via setup.py.


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
