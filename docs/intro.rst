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

    - download from bitbucket, install with setup.py
    - pip from bitbucket
    - later: pip/easy_install from pypi


Requirements
------------

    - gevent > 1.0
    - Python 2.7 required?
    - what about Python 3?


Notes for Windows users
-----------------------

    - currently, the timeout-feature does not work
    - non-blocking I/O is faked via a threadpool (significant performance drop
      compared to Unix)
    - solution would be IOCP-based (cf. libuv)


Usage
-----

    - refer to examples
    - refer to docs, especially API docs







