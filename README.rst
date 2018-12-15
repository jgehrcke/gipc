`Changelog <https://github.com/jgehrcke/gipc/blob/master/CHANGELOG.rst>`_ |
`gipc @ PyPI <https://pypi.python.org/pypi/gipc>`_ |
`gipc @ GitHub <https://github.com/jgehrcke/gipc>`_

Travis CI status (master branch): |traviscibadge|

.. |TRAVISCIBADGE| image:: https://travis-ci.org/jgehrcke/gipc.svg?branch=master
    :target: https://travis-ci.org/jgehrcke/gipc
    :align: middle

From 2012 to 2018 gipc's home was at `bitbucket.org/jgehrcke/gipc
<https://bitbucket.org/jgehrcke/gipc>`_. Since 2018 development continues on
GitHub.


Overview
========
gipc (pronunciation as in “gipsy”) provides reliable child process management
and non-blocking inter-process communication in the context of `gevent
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


Code examples
=============

Have a look at the individual programs in the `examples
<https://github.com/jgehrcke/gipc/blob/master/examples>`_ directory.



Documentation
=============
Visit https://gehrcke.de/gipc for installation instructions, API docs, code
examples, and in-depth information.


Platform support
================
The current version of gipc works on CPython 2.7/3.4/3.5/3.6/3.7. It requires
gevent 1.2 or 1.3 and supports both, Unix-like systems as well as Windows. On
Unix-like systems, gipc also works with PyPy2.7 and PyPy3. gipc's test suite is
automatically executed on Linux, Darwin (macOS), and Windows.

Who uses it?
============

- `pyethapp <https://github.com/ethereum/pyethapp>`_
- `disco <https://github.com/b1naryth1ef/disco>`_ (Discord Python library)
- `bliss <https://bliss.gitlab-pages.esrf.fr/bliss/index.html>`_
- `esdocs <https://github.com/jaddison/esdocs>`_
- `Wishbone <https://wishbone.readthedocs.io>`_
- `Quantopian’s remote Python debugger <https://github.com/quantopian/qdb>`_
- `Ajenti <http://ajenti.org/>`_
- `HoneyBadgerBFT <https://github.com/initc3/HoneyBadgerBFT-Python>`_
- `iDigBio <https://github.com/iDigBio/idb-backend>`_
- `Chronology <http://chronology.github.io>`_
- `GDriveFS <https://github.com/dsoprea/GDriveFS>`_
- `NetCall <https://github.com/aglyzov/netcall>`_
- `SiteScan <https://github.com/jasonsheh/SiteScan>`_
- `PokeAlarm <https://github.com/PokeAlarm/PokeAlarm>`_
- `gipcrpc <https://github.com/studio-ousia/gipcrpc>`_
- `etcd-gevent <https://github.com/wjsi/etcd-gevent>`_

Are you successfully using gipc in your project? Please drop me a line!


How to run the tests?
=====================
gipc's tests are written for `pytest <http://pytest.org>`_. With the
repository's root directory being the current working directory you can run the
tests like this::

    $ pip install -r requirements-tests.txt
    $ cd test && pytest -vv --cov-report term --cov-report html --cov gipc


Contact & help
==============
Your feedback and questions are highly appreciated. Please contact me via mail
at jgehrcke@googlemail.com or use the `GitHub issue tracker
<https://github.com/jgehrcke/gipc/issues>`_.


Author & license
================
gipc is written and maintained by `Jan-Philip Gehrcke <https://gehrcke.de>`_.
It is licensed under the MIT license (see LICENSE file).

I am thankful for all contributions (bug reports, code, great questions) from:

- Guy Rozendorn
- John Ricklefs
- Heungsub Lee
- Alex Besogonov
- Jonathan Kamens
- Akhil Acharya
- John Porter
- James Addison
- Oliver Margetts
- ... and others
