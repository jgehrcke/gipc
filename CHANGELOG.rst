Version 1.0.1 (Feb 21, 2019)
----------------------------

This release adds support for gevent 1.4.

Test / continuous integration changes:

- The Linux main test matrix now covers gevent 1.2.x, gevent 1.3.x, and gevent
  1.4.x.

- The PyPy tests now additionally cover pypy3.5-7.0.0 and pypy2.7-7.0.0.


Version 1.0.0 (Dec 15, 2018)
----------------------------

New platform support:

- Add support for PyPy on Linux. Thanks to Oliver Margetts and to Heungsub
  Lee for patches.

Fixes:

- Fix a bug as of which gipc crashed when passing "raw" pipe handles between
  processes on Windows (see
  `issue #63 <https://github.com/jgehrcke/gipc/issues/68>`_).

- Fix ``can't pickle gevent._semaphore.Semaphore`` error on Windows.

- Fix ``ModuleNotFoundError`` in ``test_wsgi_scenario``.

- Fix signal handling in example ``infinite_send_to_child.py``.

- Work around segmentation fault after fork on Mac OS X (affected
  ``test_wsgi_scenario`` and example program ``wsgimultiprocessing.py``).

Test / continuous integration changes:

- Fix a rare instability in ``test_exitcode_previous_to_join``.

- Make ``test_time_sync`` more stable.

- Run the example programs as part of CI (run all on Linux and Mac, run most
  on Windows).

- Linux main test matrix (all combinations are covered):

  - gevent dimension: gevent 1.2.x, gevent 1.3.x.

  - Python implementation dimension: CPython 2.7, 3.4, 3.5, 3.6, PyPy2.7, PyPy3.

- Also test on Linux: CPython 3.7, pyenv-based PyPy3 and PyPy2.7 (all with
  gevent 1.3.x only).

- Mac OS X tests (all with gevent 1.3.x):

  - pyenv Python builds: CPython 2.7, 3.6, PyPy3

  - system CPython

- On Windows, test with gevent 1.3.x and CPython 2.7, 3.4, 3.5, 3.6, 3.7.


Potentially breaking changes:

- gevent 1.1 is not tested anymore.
- CPython 3.3 is not tested anymore.


Version 0.6.0 (Jul 22, 2015)
----------------------------

- Add support for CPython 3.3 and 3.4.

- Require gevent >= 1.1b1.


Version 0.5.0 (Oct 22, 2014)
----------------------------
- Improve large message throughput on Linux (see
  `issue #13 <https://github.com/jgehrcke/gipc/issues/13>`_).

- Work around read(2) system call flaw on Mac OS X (see
  `issue #13 <https://github.com/jgehrcke/gipc/issues/13>`_)

- Work around signal.NSIG-related problem on FreeBSD (see
  `issue #10 <https://github.com/jgehrcke/gipc/issues/10>`_)

- Do not alter SIGPIPE action during child bootstrap (breaking change,
  (see `issue #12 <https://github.com/jgehrcke/gipc/issues/12>`_)).


Version 0.4.0 (Dec 07, 2013)
----------------------------
- Implement data (de)serialization pipe API (allowing for raw byte
  transmission and for custom encoders/decoders).

- Restore default signal disposition in child wrapper for all signals (see
  `issue #7 <https://github.com/jgehrcke/gipc/issues/7>`_).

- Fix DeprecationWarning related to _PairContext class (see
  `issue #5 <https://github.com/jgehrcke/gipc/issues/5>`_).

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
- Fix `issue #1 <https://github.com/jgehrcke/gipc/issues/1>`_: don't
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
