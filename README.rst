`Changelog <https://bitbucket.org/jgehrcke/gipc/src/tip/CHANGELOG.rst>`_ |
`gipc @ PyPI <https://pypi.python.org/pypi/gipc>`_ |
`gipc @ Bitbucket <https://bitbucket.org/jgehrcke/gipc>`_


Overview
========
gipc (pronunciation “gipsy”) provides reliable child process management and
inter-process communication (IPC) in the context of gevent.

Usage of Python's multiprocessing package in the context of a gevent-powered
application may raise problems and most likely breaks the application in various
subtle ways. gipc is developed with the motivation to solve many of these issues
transparently. With gipc, multiprocessing.Process-based child processes can
safely be created anywhere within your gevent-powered application. The API of
multiprocessing.Process objects is provided in a gevent-cooperative fashion.
Furthermore, gipc comes up with a pipe-based transport layer for
gevent-cooperative inter-process communication and useful helper constructs.
gipc is lightweight and simple to integrate.


Documentation
=============
Please visit https://gehrcke.de/gipc for finding API documentation, code
examples, and in-depth information.


Supported platforms
===================
The current version of gipc has been tested on CPython 2.6/2.7/3.3/3.4. It
requires gevent 1.1 and supports both, Unix-like systems and Windows.


Is gipc reliable?
=================
This is an important question, because the matter gipc is dealing with (a
delicate combination of fork, threads, leightweight threads, signals, and an
event loop library) bears the potential for various kinds of corner-case
disasters. The best answer probably is that gipc is backed by an extensive unit
test suite and the following projects are happily making use of it:

    - `Quantopian’s remote Python debugger <https://github.com/quantopian/qdb>`_
    - `Ajenti <http://ajenti.org/>`_
    - `Chronology <http://chronology.github.io>`_
    - `GDriveFS <https://github.com/dsoprea/GDriveFS>`_
    - `NetCall <https://github.com/aglyzov/netcall>`_

Are you successfully using gipc in your project? I would appreciate if you
dropped me a quick line.


Unit tests and code audit
=========================
If you run into troubles with gipc, it is a good idea to run the unit test suite
under your conditions. gipc's unit tests are written for
`pytest <http://pytest.org>`_. With ``gipc/test`` (included in the release)
being the current working directory, I usually run tests like this::

    $ py.test -v

Other than that, I use `pep8 <http://pypi.python.org/pypi/pep8>`_ and `pylint
<http://pypi.python.org/pypi/pylint>`_ for code audit. Have a look at
``audit.sh`` in the code repository. Unit test code coverage analysis requires
`coverage <http://pypi.python.org/pypi/coverage>`_ and `pytest-cov
<http://pypi.python.org/pypi/pytest-cov>`_. ``audit.sh`` leaves behind a
coverage HTML report in the test directory.


Contact & help
==============
Your feedback and questions are highly appreciated. Please contact me via mail
at jgehrcke@googlemail.com or use the `Bitbucket issue tracker
<https://bitbucket.org/jgehrcke/gipc/issues>`_.


Author & license
================
gipc is written and maintained by `Jan-Philip Gehrcke <http://gehrcke.de>`_.
It is licensed under an MIT license (see LICENSE file).
