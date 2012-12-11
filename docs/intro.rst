Introduction
------------
With ``gipc`` you can easily use ``multiprocessing`` and ``gevent`` within one Python application.


**What does gipc provide?**

    - gevent-aware ``multiprocessing.Process``-based child processes.
    - gevent-aware inter-process communication (a lot of dashes, huh?).


**Isn't this achievable with just gevent+multiprocessing?**

It is, and this is precisely what ``gipc`` does. It just requires at lot of care:
On Unix, child process creation via Python's ``multiprocessing`` package in the
context of ``gevent`` might yield an undesired event loop state in the child and
most likely breaks your application in some way. Furthermore, blocking method calls
such as ``join()`` on a ``multiprocessing.Process`` or the ``send()``/``recv()`` methods
on a ``multiprocessing.Pipe`` are not gevent-cooperative. ``gipc`` hides and
solves these problems for you in a straight-forward fashion and allows for
simple integration of child processes in your application.


Installation
------------

Directly via setup.py
^^^^^^^^^^^^^^^^^^^^^
Download the latest release from `PyPI <http://pypi.python.org/pypi/gipc/>`_ or the latest development version from the `code repository at bitbucket <https://bitbucket.org/jgehrcke/gipc>`_. Extract the archive and invoke::

    $ python setup.py install


Via pip
^^^^^^^
You can use `pip <http://www.pip-installer.org>`_ for downloading and installing gipc from PyPI in one step::

    $ pip install gipc

For installing pip, ...

pip is recommended over easy_install.

You can also install the development version of gipc via pip: ...


Requirements
------------

    - gevent > 1.0
    - Python 2.7 (also 2.6)
    - Python 3 support: TBD


Notes for Windows users
-----------------------

    - Currently, the ``get()`` timeout feature does not work
    - non-blocking I/O is faked via a threadpool (significant performance drop
      compared to Unix), a solution would be IOCP-based (cf. libuv)


Usage
-----

    - cf. Examples section
    - cf. API section







