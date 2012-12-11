gipc: multiprocessing and IPC for gevent
========================================


Introduction
------------

With ``gipc`` you can easily integrate gevent-aware
``multiprocessing.Process``-based child processes into your application.
Furthermore, ``gipc`` provides pipe-based gevent-aware inter-process
communication (a lot of dashes, huh?).

On Unix, child process creation via Python's ``multiprocessing`` package in the
context of ``gevent`` might yield an undesired event loop state in the child and
most likely breaks your application in some way. Blocking method calls such
``join()`` on a ``multiprocessing.Process`` or the ``send()``/``recv()`` methods
on a ``multiprocessing.Pipe`` are not gevent-cooperative. ``gipc`` hides and
solves these problems for you in a straight-forward fashion and allows for
simple integration of child processes in your application.


Installation
------------

    - pip/easy_install pypi
    - download from bitbucket, install with setup.py
    - pip from bitbucket


Requirements
------------
    
    - built for gevent > 1.0
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

    - simple example
    - refer to docs, especially API docs
    

