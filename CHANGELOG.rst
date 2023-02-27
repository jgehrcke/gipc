Version 1.5.0 (Feb 27, 2023)
----------------------------

This release adds support for gevent 22.12.2 and for Python 3.11.

Continuous integration changes:

- Cover CPython 3.11 (Linux, Windows, macOS).
- Cover PyPy 3.9.
- Do not test with Python 3.6 anymore.

Version 1.4.0 (Feb 08, 2022)
----------------------------

This release adds support for gevent 21.12.0 and for Python 3.10.

Continuous integration changes:

- Cover CPython 3.10 (Linux, Windows, macOS)
- Cover PyPy 3.8 instead of PyPy 3.6 (Linux, macOS)


Version 1.3.0 (July 23, 2021)
-----------------------------

This release adds support for gevent 21.x and CPython 3.8+ on macOS (thanks to
Tyler Willey for crunching through this).

On macOS with CPython 3.8 and newer, gipc now supports the new default
``multiprocessing`` process invocation method which is based on ``spawn()``, similar
to ``CreateProcess()`` on win32. Depending on the needs of your application, you
may want to explore setting the process invocation method back to ``fork()`` via
``multiprocessing.set_start_method('fork')``.


Version 1.2.0 (Jun 3, 2021)
---------------------------

This release adds support for gevent 21.x on Linux and Windows, tested with
CPython 3.6, 3.7, 3.8, and 3.9.

For macOS, this gipc release still does not support CPython 3.8 and newer.

Version 1.1.1 (Jan 03, 2021)
----------------------------

This release

- adds support for gevent 1.5 on Linux, macOS, and Windows.

- adds CPython 3.8 support for Linux and Windows.

The combination of gevent 1.5.0 (and newer), CPython 3.8 and Darwin (macOS) is
not supported. Adding support is tracked in `issue #100 <https://github.com/jgehrcke/gipc/issues/100>`_.


Continuous integration changes:

- Moved from Travis CI (and AppVeyor) to GitHub Actions, in view of `sadness <https://news.ycombinator.com/item?id=18978251>`_
  affecting so many open source projects.

- gevent 1.2.x, 1.3.x, 1.4.x are not covered anymore by CI (1.4.x still works, though).

- CPython 2.7 and PyPy 2.7 are not covered anymore (should still work with this release, though).

- Newer CPython and PyPy releases are covered by automatic testing now.

Note: the next version of gipc is likely to

- only support gevent 20.x and newer

- not support CPython 2.7 anymore

As these are significat compatibility changes, the next gipc release will most likely have version 2.0.


Version 1.1.0 (Feb 18, 2020)
----------------------------

This release adds compatibility with the
``multiprocessing.Process.close()``
`method <https://docs.python.org/3.8/library/multiprocessing.html#multiprocessing.Process.close>`_
that was `introduced <https://bugs.python.org/issue30596>`_ with CPython 3.7.

Platform support / continuous integration changes:

- The Linux test matrix now covers gevent 1.2.2, gevent 1.3.7, gevent 1.4.0, and
  gevent 1.5a3.

- PyPy:

  - On Linux, test with ``pypy2.7-7.3.0`` and ``pypy3.6-7.3.0``. Do not test
    anymore with ``pypy3.5-6.0.0``, ``pypy3.5-7.0.0``, ``pypy2.7-6.0.0``,
    ``pypy2.7-7.0.0``.

  - On Darwin, test with only ``pypy3.6-7.3.0``.

- On Darwin, gipc is now tested with CPython 3.7, too (previously only tested up
  to 3.6).

Note that gipc was found to work fine with CPython 3.8 and gevent 1.5 on Linux.
This has been tested with the gevent 1.5a3 pre-release (which you will have to
install explicitly before installing gipc to try out gipc and gevent with
CPython 3.8). Another gipc release will be made once gevent 1.5 has left the
alpha stage.


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
