************
Introduction
************

What can gipc do for you?
=========================
With ``gipc`` you can easily use ``multiprocessing`` and ``gevent`` within one Python application. It provides

    - gevent-aware ``multiprocessing.Process``-based child processes.
    - gevent-cooperative inter-process communication.


Isn't this achievable with just gevent+multiprocessing?
=======================================================
It is, and this is precisely what ``gipc`` does. It just requires some care:
On Unix, child process creation via Python's ``multiprocessing`` package in the
context of ``gevent`` might yield an undesired event loop state in the child and
most likely breaks your application in some way. Furthermore, blocking method calls
such as ``join()`` on a ``multiprocessing.Process`` or the ``send()``/``recv()`` methods
on a ``multiprocessing.Connection`` are not gevent-cooperative. ``gipc`` hides and
solves these problems for you in a straight-forward fashion and allows for
simple integration of child processes in your application.


Installation
============

Via pip
-------
The latest ``gipc`` release from PyPI can be pulled and and installed via `pip <http://www.pip-installer.org>`_::

    $ pip install gipc

pip can also install the development version of ``gipc`` via::

    $ pip install hg+https://bitbucket.org/jgehrcke/gipc

Note that the latter requires the most recent version of `distribute <http://packages.python.org/distribute/>`_ which can be installed by executing `distribute_setup.py <http://python-distribute.org/distribute_setup.py>`_.

pip is recommended over easy_install. pip installation instructions can be found `here <http://www.pip-installer.org/en/latest/installing.html>`_.


Directly via setup.py
---------------------
Download the latest release from `PyPI <http://pypi.python.org/pypi/gipc/>`_.  Extract the archive and invoke::

    $ python setup.py install

The same can be done with the latest development version of ``gipc`` which can be downloaded from `bitbucket <https://bitbucket.org/jgehrcke/gipc>`_.

Once installed, you should be able to remove gipc manually or via ``pip uninstall gipc``.


Requirements
============
    - gevent >= 1.0 (tested against gevent 1.0rc2)
    - Python 2.6, 2.7
    - Python 3 support: TBD


Notes for Windows users
=======================
    - The ``get()`` timeout feature is not available.
    - Non-blocking I/O is faked via a threadpool (significant performance drop
      compared to Unix).
    - A solution to both problems would be IOCP-based (cf. libuv).


Usage
=====

    - cf. Examples section
    - cf. API section







