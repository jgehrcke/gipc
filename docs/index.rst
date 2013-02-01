.. gipc documentation master file, created by
   sphinx-quickstart on Thu Nov 22 15:14:51 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


.. toctree::
    :hidden:
    :maxdepth: 2

========================================
gipc: multiprocessing and IPC for gevent
========================================

**Table of contents:**

    - :ref:`About gipc <about>`
        - :ref:`What can gipc do for you? <what>`
        - :ref:`Usage <usage>`
        - :ref:`Technical notes <technotes>`
        - :ref:`Installation and requirements <installation>`
        - :ref:`Notes for Windows users <winnotes>`
        - :ref:`Author, license, contact <contact>`
    - :ref:`Code examples <examples>`
    - :ref:`API documentation <api>`
        - :ref:`Spawning child processes <api_spawn>`
        - :ref:`Creating a pipe and its handle-pair <api_pipe_create>`
        - :ref:`Handling handles <api_handles>`
        - :ref:`Controlling child processes <api_control_childs>`
        - :ref:`Exception types <api_exceptions>`


This documentation applies to gipc |release|. It was built on |today|.


.. _about:

About gipc
##########


.. _what:

What can gipc do for you?
=========================

Naive usage of ``multiprocessing`` in the context of a ``gevent``-powered
application may raise various problems and most likely breaks the application
in some way. ``gipc`` is developed with the motivation to solve these issues
transparently and make using ``gevent`` in combination with the basics of
``multiprocessing`` -- process creation and IPC -- a no-brainer again.

**With gipc (pronunciation "gipsy") multiprocessing.Process-based child
processes can safely be created anywhere within your gevent-powered application.
Furthermore, gipc provides gevent-cooperative inter-process communication and
useful helper constructs.**

``gipc`` is lightweight and very simple to integrate. In the following code
snippet, a Python object is sent from a greenlet in the main process to a child
process::

    import gevent
    import gipc

    obj = 0

    def child(reader):
        assert reader.get() == obj

    if __name__ == "__main__":
        with gipc.pipe() as (reader, writer):
            writelet = gevent.spawn(lambda w: w.put(obj), writer)
            readchild = gipc.start_process(child, args=(reader,))
            writelet.join()
            readchild.join()

Although very simple, this code would have malicious side effects if used with
the canonical ``p = multiprocessing.Process(); p.start()`` instead of
``gipc.start_process()``.


.. _usage:

Usage
=====

``gipc``'s interface is small and the usage is pretty simple. Make yourself
comfortable with ``gipc.start_process()`` and ``gipc.pipe()`` by going through
the :ref:`examples <examples>` and the :ref:`API <api>` section.


What are the challenges and what is gipc's approach?
----------------------------------------------------

Depending on the operating system, child process creation via
``multiprocessing`` in the context of ``gevent`` might yield a malicious event
loop state in the child. Furthermore, greenlets spawned before forking are
duplicated in the child. In addition, blocking method calls such as ``join()``
on a ``multiprocessing.Process`` or the ``send()``/``recv()`` methods on a
``multiprocessing.Connection`` are not gevent-cooperative. ``gipc`` overcomes
these challenges for you transparently and in a straight-forward fashion.
It allows for simple integration of child processes in your application -- on
POSIX-compliant systems as well as on Windows.


Can't I just use gevent+multiprocessing?
----------------------------------------

A solid application based on ``gevent`` and ``multiprocessing`` requires a lot
of care and dealing with special cases. ``gipc`` is only a thin wrapper and
provides the latter. Of course you can do this yourself. Feel free to have a
look at gipc's code.


.. _technotes:

Technical notes
===============
- ``gipc`` uses classical anonymous pipes as transport layer for
  gevent-cooperative communication between greenlets and/or processes. A binary
  ``pickle`` protocol is used for transmitting arbitrary objects. Reading and
  writing on pipes is done with ``gevent``'s cooperative versions of
  ``os.read()`` and ``os.write()`` (on POSIX-compliant systems they use
  non-blocking I/O, on Windows a threadpool is used). On Linux, my test system
  (Xeon E5630) achieved a payload transfer rate of 1200 MB/s and a message
  transmission rate of 100.000 messages/s through one pipe between two
  processes.

- Child process creation and invocation is done via a thin wrapper around
  ``multiprocessing.Process``. On Unix, the gevent's state and the libev event
  loop are re-initialized in the child before execution of the target function.

- On POSIX-compliant systems, gevent-aware child process monitoring is based on
  libev child watchers (this affects ``is_alive()`` and ``join()``).

- Convenience features such as a context manager for pipe handles or timeout
  controls based on ``gevent.Timeout`` are available.

- Any read/write operation on a pipe is ``gevent.lock.Semaphore``-protected
  and therefore greenlet-/threadsafe and atomic.

- ``gipc`` obeys `semantic versioning 2 <http://semver.org/>`_.

- Although ``gipc`` is in an early development phase, I found it to work very
  stable already. The unit test suite aims to cover all of ``gipc``'s features
  within a clean gevent environment. More complex application scenarios,
  however, are not covered so far. Please let me know in which cases
  ``gipc`` + ``gevent`` fails for you.


.. _installation:

Installation
============

Requirements
------------

- gevent >= 1.0 (tested against gevent 1.0rc2). Download gevent
  `here <https://github.com/SiteSupport/gevent/downloads>`_.
- unit tests pass on Python 2.6 and 2.7.

Install via pip
---------------

The latest ``gipc`` release from PyPI can be pulled and and installed via
`pip <http://www.pip-installer.org>`_::

    $ pip install gipc

pip can also install the development version of ``gipc``::

    $ pip install hg+https://bitbucket.org/jgehrcke/gipc

Note that the latter requires the most recent version of
`distribute <http://packages.python.org/distribute/>`_ which can be installed
by executing `distribute_setup.py <http://python-distribute.org/distribute_setup.py>`_.

pip is recommended over easy_install. pip installation instructions can be
found `here <http://www.pip-installer.org/en/latest/installing.html>`_.


Install directly via setup.py
-----------------------------

Download the latest release from `PyPI <http://pypi.python.org/pypi/gipc/>`_.
Extract the archive and invoke::

    $ python setup.py install

The same can be done with the latest development version of ``gipc`` which
can be downloaded from `bitbucket <https://bitbucket.org/jgehrcke/gipc>`_.

Once installed, you can remove gipc manually or via ``pip uninstall gipc``.


.. _winnotes:

Notes for Windows users
=======================

- The ``_GIPCReader.get()`` timeout feature is not available.
- "Non-blocking I/O" is realized by outsourcing blocking I/O calls to threads
  in a gevent thread pool. Compared to native non-blocking I/O as is available
  on POSIX-compliant systems, this leads to a significant messaging performance
  drop.

`Windows I/O Completion Ports <http://msdn.microsoft.com/en-us/library/aa365198%28VS.85%29.aspx>`_
(IOCP) could solve both issues in an elegant way. Currently, gevent is built on
top of libev which does not support IOCP. In the future, however, gevent might
become `libuv <https://github.com/joyent/libuv>`_-backed. libuv supports IOCP
and would allow for running the same gevent code on Windows as on
POSIX-compliant systems. Furthermore, if gevent went with libuv, the strengths
of both, the node.js and the gevent worlds would be merged. Denis Bilenko, the
maintainer of gevent, seems to be `open <https://twitter.com/gevent/status/251870755187478529>`_
to such a transition and the first steps are already
`done <https://github.com/saghul/uvent>`_.


.. _contact:

Author, license, contact
========================

``gipc`` is written and maintained by
`Jan-Philip Gehrcke <http://gehrcke.de>`_ and is licensed under the
`Apache License 2.0 <http://www.apache.org/licenses/LICENSE-2.0.txt>`_.
Your feedback is highly appreciated. You can contact me at
jgehrcke@googlemail.com or use the
`Bitbucket issue tracker <https://bitbucket.org/jgehrcke/gipc/issues>`_.


.. _examples:

Examples
########

- :ref:`gipc.pipe()-based IPC <exampleipc>`
- :ref:`Serving multiple clients (in child) from one server (in parent) <exampleserverclient>`
- :ref:`Time-synchronization between processes <examplesync>`


.. _exampleipc:

gipc.pipe()-based messaging from greenlet in parent to child
============================================================

Some basic concepts are explained by means of this simple messaging example:

.. code::

    import gevent
    import gipc


    def main():
        with gipc.pipe() as (r, w):
            p = gipc.start_process(target=child_process, args=(r, ))
            wg = gevent.spawn(writegreenlet, w)
            try:
                p.join()
            except KeyboardInterrupt:
                wg.kill(block=True)
                p.terminate()
            p.join()


    def writegreenlet(writer):
        while True:
            writer.put("written to pipe from a greenlet running in the main process")
            gevent.sleep(1)


    def child_process(reader):
        while True:
            print "Child process got message from pipe:\n\t'%s'" % reader.get()


    if __name__ == "__main__":
        main()

The context manager ``with gipc.pipe() as (r, w)`` creates a pipe with read
handle ``r`` and write handle ``w``. On context exit (latest) the pipe ends will
be closed properly.

Within the context, a child process is spawned via ``gipc.start_process()``.
The read handle ``r`` is provided to the child process. It calls
``child_process(r)`` where an endless loop waits for objects on the read end of
the pipe. Upon retrieval, it immediately prints them.

While child process ``p`` is running, a greenlet ``wg`` is started in the main
process. It executes the function ``writegreenlet`` while providing
``gipc._GIPCWriter`` ``w`` as an argument. Within this greenlet, one string per
second is written to the write end of the pipe.

After spawning ``wg``, ``p.join()`` is called immediately, i.e. the write
greenlet is running while ``p.join()`` waits for the child process to terminate.
In this state, messages are passed between parent and child until a
``KeyboardInterrupt`` exception is raised in the parent.

On ``KeyboardInterrupt``, the parent first kills the write greenlet and blocks
cooperatively until it has stopped. Then it tries to terminate the child process
(via ``SIGTER`` on Unix) and waits for it to exit via ``p.join()``.


.. _exampleserverclient:

Serving multiple clients (in child) from one server (in parent)
===============================================================

This example implements TCP communication between a server in the parent
process and multiple clients in a child process:

1)  gevent's ``StreamServer`` is started in a greenlet within the initial
    (parent) process. For each connecting client, it receives one
    newline-terminated message and echoes it back.

2)  A child process is started using gipc. Its starting point is the function
    ``clientprocess``. There, N TCP clients are started concurrently from N
    greenlets.

3)  Each client sends one message, validates the echo response and terminates.

4)  The child process terminates.

5)  After the child process is joined in the parent, the server is killed.

6)  The server greenlet is joined.

Output on my test machine:
1000 clients served within 0.54 s.

.. code::

    import gevent
    from gevent.server import StreamServer
    from gevent import socket
    import gipc
    import time


    PORT = 1337
    N_CLIENTS = 1000
    MSG = "HELLO\n"


    def serve(sock, addr):
        f = sock.makefile()
        f.write(f.readline())
        f.flush()
        f.close()


    def server():
        ss = StreamServer(('localhost', PORT), serve).serve_forever()


    def clientprocess():
        t1 = time.time()
        clients = [gevent.spawn(client) for _ in xrange(N_CLIENTS)]
        gevent.joinall(clients)
        duration = time.time()-t1
        print "%s clients served within %.2f s." % (N_CLIENTS, duration)


    def client():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', PORT))
        f = sock.makefile()
        f.write(MSG)
        f.flush()
        assert f.readline() == MSG
        f.close()


    if __name__ == "__main__":
        s = gevent.spawn(server)
        c = gipc.start_process(clientprocess)
        c.join()
        s.kill()
        s.join()


.. _examplesync:

Time-synchronization between processes
======================================

Child process creation may take a significant amount of time, especially on
Windows. This time is not predictable.

Often, the code in the parent should only proceed in the moment
the child and the code in the child have reached a certain state.
Applications must not rely on a child process "probably being up and running by
now" or on "sufficient" constant waiting times. The proper way to tackle this
is a bi-directional synchronization mechanism:

- Process A sends a synchronization request to process B and waits for an
  acknowledgement response. It proceeds upon retrieval.
- Process B sends the acknowledgement in the moment it retrieves the sync
  request and proceeds.

This concept can easily be implemented using two ``gipc.pipe()s``:

.. code::

    import time
    import gevent
    import gipc


    def main():
        with gipc.pipe() as (r1, w1):
            with gipc.pipe() as (r2, w2):
                p = gipc.start_process(
                    writer_process,
                    kwargs={'writer': w2, 'syncreader': r1}
                    )
                result = None
                # Synchronize with child process.
                w1.put("SYN")
                assert r2.get() == "ACK"
                # SYNC
                t = time.time()
                while result != "STOP":
                    result = r2.get()
                elapsed = time.time() - t
                p.join()
                print "Time elapsed: %.3f s" % elapsed


    def writer_process(writer, syncreader):
        with writer:
            assert syncreader.get() == "SYN"
            writer.put("ACK")
            # SYNC
            for i in xrange(1000):
                writer.put("A" * 1000)
            writer.put('STOP')


    if __name__ == "__main__":
        main()

The code blocks marked with ``# SYNC`` in parent and child are entered
quasi-simultaneously.


.. _api:

gipc API
########

- :ref:`Spawning child processes <api_spawn>`
- :ref:`Creating a pipe and its handle-pair <api_pipe_create>`
- :ref:`Handling handles <api_handles>`
- :ref:`Controlling child processes <api_control_childs>`
- :ref:`Exception types <api_exceptions>`


.. _api_spawn:

Spawning child processes
========================

.. automodule:: gipc
    :members: start_process


.. _api_pipe_create:

Creating a pipe and its handle-pair
===================================

.. automodule:: gipc
   :members: pipe


.. _api_handles:

Handling handles
================

.. autoclass:: gipc.gipc._GIPCHandle()
    :members: close

.. autoclass:: gipc.gipc._GIPCWriter()
    :show-inheritance:
    :members: put

.. autoclass:: gipc.gipc._GIPCReader()
    :show-inheritance:
    :members: get


.. _api_control_childs:

Controlling child processes
===========================

.. autoclass:: gipc.gipc._GProcess()
    :show-inheritance:
    :members: join


.. _api_exceptions:

Exception types
===============

.. autoexception:: gipc.GIPCError

.. autoexception:: gipc.GIPCLocked

.. autoexception:: gipc.GIPCClosed



.. Indices and tables
.. ==================
..
.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`

