`Changelog <https://github.com/jgehrcke/gipc/blob/master/CHANGELOG.rst>`_ |
`gipc @ PyPI <https://pypi.python.org/pypi/gipc>`_ |
`gipc @ GitHub <https://github.com/jgehrcke/gipc>`_ |
`gipc @ Bitbucket <https://bitbucket.org/jgehrcke/gipc>`_ (inactive)


Overview
========
gipc (pronunciation as in “gipsy”) provides reliable child process management
and inter-process communication in the context of `gevent
<https://github.com/gevent/gevent>`_.

Direct usage of Python's `multiprocessing package
<https://docs.python.org/3/library/multiprocessing.html>`_ in the context of a
gevent-powered application is error-prone and may break the application in
various `subtle ways
<https://gehrcke.de/gipc/#what-are-the-challenges-and-what-is-gipc-s-solution>`_
. With gipc, ``multiprocessing.Process``-based child processes can safely be
created anywhere within your gevent-powered application. The API of
``multiprocessing.Process`` objects is provided in a gevent-cooperative fashion.
Also, gipc provides a pipe-based transport layer for gevent-cooperative
inter-greenlet and inter-process communication. gipc is lightweight and easy to
integrate.


Documentation
=============
Visit https://gehrcke.de/gipc for installation instructions, API docs, code
examples, and in-depth information.


Platform support
================
The current version of gipc works on CPython 2.7/3.4/3.5/3.6. It requires gevent
1.2 and supports both, Unix-like systems as well as Windows. On Unix-like
systems, gipc also works with PyPy2.7 and PyPy3. Tests are not yet automatically
run for the Windows and Darwin platforms and corresponding community feedback is
greatly appreciated.


Who uses it?
============

    - `Wishbone <https://wishbone.readthedocs.io>`_
    - `Quantopian’s remote Python debugger <https://github.com/quantopian/qdb>`_
    - `Ajenti <http://ajenti.org/>`_
    - `PokeAlarm <https://github.com/PokeAlarm/PokeAlarm>`_
    - `Chronology <http://chronology.github.io>`_
    - `GDriveFS <https://github.com/dsoprea/GDriveFS>`_
    - `NetCall <https://github.com/aglyzov/netcall>`_
    - `gipcrpc <https://github.com/studio-ousia/gipcrpc>`_


Are you successfully using gipc in your project? Please drop me a line!


How to run tests and code audit?
================================
gipc's tests are written for `pytest <http://pytest.org>`_. With the
repository's root directory being the current working directory, run tests and
audit like this::

    $ pip install -r requirements-tests.txt
    $ ./audit.sh
    $ cd test && pytest -vv --cov-report term --cov-report html --cov gipc


Contact & help
==============
Your feedback and questions are highly appreciated. Please contact me via mail
at jgehrcke@googlemail.com or use the `GitHub issue tracker
<https://github.com/jgehrcke/gipc/issues>`_.


Author & license
================
gipc is written and maintained by `Jan-Philip Gehrcke <http://gehrcke.de>`_.
It is licensed under an MIT license (see LICENSE file).
