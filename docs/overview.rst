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

.. _installation:

Download & installation
=======================
The latest gipc release from PyPI can be downloaded and installed via
`pip <https://pip.pypa.io/en/stable/>`_::

    $ pip install gipc

pip can also install the current development version of gipc::

    $ pip install git+https://github.com/jgehrcke/gipc

gipc obeys `semantic versioning <http://semver.org/>`_.


.. _platforms:

Platform support
================
The current version of gipc works on CPython 2.7/3.4/3.5/3.6. It has been tested
against gevent 1.2 and supports both, Unix-like systems as well as Windows. On
Unix-like systems, gipc also works with PyPy2.7 and PyPy3. Tests are not
automatically run for the Windows and Darwin platforms and corresponding
community feedback is greatly appreciated.
