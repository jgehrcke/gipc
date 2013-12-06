
What is gipc?
=============
Usage of Python's multiprocessing package in the context of a
gevent-powered application may raise various problems and most likely breaks
the application in many ways.

gipc (pronunciation "gipsy") is developed with the motivation to solve many of these
issues transparently. With gipc, multiprocessing.Process-based child processes
can safely be created anywhere within your gevent-powered application. The API
of multiprocessing.Process objects is provided in a gevent-cooperative fashion.
Furthermore, gipc comes up with a pipe-based transport layer for
gevent-cooperative inter-process communication and useful helper constructs.
gipc is lightweight and simple to integrate.


What are the boundary conditions?
=================================
Currently, gipc is developed against gevent 1.0. It is tested on CPython 2.6
& 2.7 on Linux as well as on Windows. Python 3 will be supported as soon as
gevent supports it.


Where are documentation and changelog?
======================================
    - API documentation and further details: http://gehrcke.de/gipc.
    - Changelog: `Here <https://bitbucket.org/jgehrcke/gipc/src/tip/CHANGELOG.rst>`_,
      hosted at Bitbucket.


Is gipc reliable?
=================
Development of gipc began in late 2012, so it is still not being mature.
However, as of version 0.3, I am not aware of severe issues. To my
knowledge, gipc has already been deployed in serious projects. Generally, you
should be aware of the fact that mixing any of fork, threads, greenlets and an
event loop library such as libev bears the potential for various kinds of
corner-case disasters. One could argue that ``fork()`` in the
context of libev without doing a clean ``exec`` in the child already *is*
broken design. However, many people would like to do exactly this and gipc's
basic approach has proven to work in such cases. gipc is developed with a
strong focus on reliability and with best intentions in mind,
and via unit testing, gipc has been validated to work reliably in scenarios of
low and medium complexity. Of course, gipc cannot rescue an a priori ill-posed
approach. Now it is up to you to evaluate gipc in the context of your project
-- please let me know how gipc performs for you.


Where should I download gipc?
=============================
    - Releases: `PyPI <http://pypi.python.org/pypi/gipc>`_.
    - Development version: `Hg repository <https://bitbucket.org/jgehrcke/gipc>`_.


How can the unit tests be run?
==============================
If you run into troubles with gipc, it is a good idea to run the unit test suite
under your conditions. gipc's unit tests are written for
`pytest <http://pytest.org>`_. With ``gipc/test`` (included in the release)
being the current working directory, I usually run tests like this::

    $ py.test -v


How is code audit perfomed?
===========================
I use `pep8 <http://pypi.python.org/pypi/pep8>`_ and
`pylint <http://pypi.python.org/pypi/pylint>`_. Have a look at ``audit.sh`` in
the code repository. Unit test code coverage analysis requires
`coverage <http://pypi.python.org/pypi/coverage>`_ and
`pytest-cov <http://pypi.python.org/pypi/pytest-cov>`_. ``audit.sh`` leaves
behind a coverage HTML report in the ``coverage_html`` directory.


Contact & help
==============
Your feedback and questions are highly appreciated. For now, please contact me
via mail at jgehrcke@googlemail.com or use the
`Bitbucket issue tracker <https://bitbucket.org/jgehrcke/gipc/issues>`_.


Author & license
================
gipc is written and maintained by `Jan-Philip Gehrcke <http://gehrcke.de>`_.
It is licensed under an MIT license (see LICENSE file).
