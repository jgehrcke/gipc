.. _overview:

********
Overview
********

Direct usage of Python's `multiprocessing package
<https://docs.python.org/3/library/multiprocessing.html>`_ in the context of a
gevent-powered application is error-prone and may break the application in
various subtle ways (see :ref:`Challenges <challenges>`).

With gipc, ``multiprocessing.Process``-based child processes can safely be
created anywhere within your gevent-powered application. The API of
``multiprocessing.Process`` objects is provided in a gevent-cooperative fashion.
Also, gipc provides a pipe-based transport layer for gevent-cooperative
inter-greenlet and inter-process communication. gipc is lightweight and easy to
integrate (see code
:ref:`examples <examples>`, :ref:`API reference<api>`).

gipc is used by, among others,
`Quantopian's <https://www.quantopian.com>`_
`remote Python debugger <https://github.com/quantopian/qdb>`_,
`Ajenti <http://ajenti.org/>`_,
`Chronology <http://chronology.github.io>`_,
`gipcrpc <https://github.com/studio-ousia/gipcrpc>`_,
`NetCall <https://github.com/aglyzov/netcall>`_,
`PokeAlarm <https://github.com/PokeAlarm/PokeAlarm>`_,
`Wishbone <https://wishbone.readthedocs.io>`_,
and `GDriveFS <https://github.com/dsoprea/GDriveFS>`_.
Are you successfully applying gipc in your project? That is always great
to hear: please :ref:`drop me a line <contact>`!


.. _platforms:

Platform support
================

The current version of gipc works on CPython 2.7/3.4/3.5/3.6/3.7. It requires
gevent 1.2 or 1.3 and supports both, Unix-like systems as well as Windows. On
Unix-like systems, gipc also works with PyPy2.7 and PyPy3. gipc's test suite is
automatically executed on Linux, Darwin (macOS), and Windows.


.. _installation:

Download & installation
=======================
The latest gipc release from PyPI can be downloaded and installed via
`pip <https://pip.pypa.io/en/stable/>`_::

    $ pip install gipc

pip can also install the current development version of gipc::

    $ pip install git+https://github.com/jgehrcke/gipc


.. _versioning:

Versioning
==========

gipc obeys `semantic versioning <http://semver.org/>`_.
