.. gipc documentation master file, created by
   sphinx-quickstart on Thu Nov 22 15:14:51 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.
   Copyright 2012-2013 Jan-Philip Gehrcke. See LICENSE file for details.

.. toctree::
    :hidden:
    :maxdepth: 2

========================================
gipc: child processes and IPC for gevent
========================================

**Table of contents:**

    - :ref:`About gipc <about>`
        - :ref:`What is gipc good for? <what>`
        - :ref:`Usage <usage>`
        - :ref:`Technical notes <technotes>`
        - :ref:`Code, requirements, download, installation <installation>`
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

gipc (pronunciation “gipsy”) is a Python package tested on CPython 2.6 and
2.7 on Linux as well as on Windows.

What is gipc good for?
======================

The usage of multiple processes in the context of `gevent <http://gevent.org>`_
in principal can be a decent solution whenever a generally I/O-limited Python
application needs to distribute tasks among multiple CPUs in parallel.

However, naive usage of Python's multiprocessing package within a gevent-powered
application may raise various problems and most likely breaks the application in
many ways. gipc is developed with the motivation to solve these issues
transparently and make using gevent in combination with multiprocessing-based
child processes and inter-process communication (IPC) a no-brainer again:

- **With gipc, multiprocessing.Process-based child
  processes can safely be created and monitored anywhere within your
  gevent-powered application. Malicious side-effects of child process creation
  in the context of gevent are prevented.**
- **The API of multiprocessing.Process objects is provided in a
  gevent-cooperative fashion.**
- **gevent natively works in children.**
- **gipc comes up with a pipe-based transport layer for gevent-cooperative
  IPC.**
- **gipc is lightweight and simple to integrate.**

In the following code snippet, a Python object is sent from a greenlet in the
main process through a pipe to a child process::

    import gevent
    import gipc

    def child(reader):
        assert reader.get() == 0

    if __name__ == "__main__":
        with gipc.pipe() as (reader, writer):
            writelet = gevent.spawn(lambda w: w.put(0), writer)
            readchild = gipc.start_process(target=child, args=(reader,))
            writelet.join()
            readchild.join()

Although quite simple, this code would have various negative side-effects if
used with the canonical multiprocessing API instead of
``gipc.start_process()`` and ``gipc.pipe()``, as outlined in the next paragrah.


What are the challenges and what is gipc's approach?
----------------------------------------------------

Depending on the operating system, child process creation via Python's
multiprocessing in the context of gevent requires special treatment. Most care
is needed on POSIX-compliant systems. There, a fork might yield a faulty libev
event loop state in the child. Most noticeable, greenlets spawned before
forking are cloned and haunt in the child upon context switch. Consider this
code running on Unix (tested with Python 2.7 & gevent 1.0rc2)::

    import gevent
    import multiprocessing

    def child(c):
        gevent.sleep(0)
        assert c.recv() == 0
        assert c.recv() == 0

    if __name__ == "__main__":
        def writelet(c):
            c.send(0)
        c1, c2 = multiprocessing.Pipe()
        writelet = gevent.spawn(writelet, c1)
        readchild = multiprocessing.Process(target=child, args=(c2,))
        readchild.start()
        writelet.join()
        readchild.join()

It runs without error. Although the code intends to send only one message to the
child through a multiprocessing ``Pipe``, the two ``assert`` statements verify
that the child actually receives two times the same message. One message is
sent -- as intended -- from the writelet in the parent through the ``c1`` end of
the pipe. It is retrieved at the ``c2`` end of the pipe in the child. The other
message is sent from the spooky writelet clone in the child. It is also written
to the ``c1`` end of the pipe which has implicitly been duplicated during
forking. Greenlet clones in the child of course only run when a context switch
is triggered; in this case via ``gevent.sleep(0)``. As you can imagine, this
behavior in general might lead to a wide range of side-effects and tedious
debugging sessions.

In addition, the code above contains several non-cooperatively blocking method
calls: ``readchild.join()`` as well as the ``send()``/``recv()`` calls (of
``multiprocessing.Connection`` objects in general) block the calling thread and
do not allow for context switches.

gipc overcomes these and other challenges for you transparently and in a
straight-forward fashion. It provides high performing gevent-cooperative
pipe-based message transport channels. Dispensable gipc pipe handles are closed
in the child. Greenlet clones are cleanly killed in the child before being
harmful. The libev event loop state is fixed in time. Basically, children start
off with a fresh gevent state before entering the user-given target function. On
POSIX-compliant systems, gipc entirely avoids multiprocessing's child monitoring
capabilities and uses libev's wonderful child watcher system.

gipc allows for integration of child processes in your application via a simple
API -- on POSIX-compliant systems as well as on Windows.


.. _usage:

Usage
=====

gipc's usage is pretty simple. Its interface is clear and slim. Make yourself
comfortable with ``gipc.start_process()`` and ``gipc.pipe()`` by going through
the :ref:`examples <examples>` and the :ref:`API <api>` section.


.. _technotes:

Technical notes
===============
- gipc uses classical anonymous pipes as transport layer for
  gevent-cooperative communication between greenlets and/or processes. A binary
  ``pickle`` protocol is used for transmitting arbitrary objects. Reading and
  writing on pipes is done with ``gevent``'s cooperative versions of
  ``os.read()`` and ``os.write()`` (on POSIX-compliant systems they use
  non-blocking I/O, on Windows a threadpool is used). On Linux, my test system
  (Xeon E5630) achieved a payload transfer rate of 1200 MB/s and a message
  transmission rate of 100.000 messages/s through one pipe between two
  processes.

- Child process creation and invocation is done via a thin wrapper around
  ``multiprocessing.Process``. On Unix, gevent's state and the libev event
  loop are re-initialized in the child before execution of the target function.

- On POSIX-compliant systems, gevent-aware child process monitoring is based on
  libev child watchers (this affects ``is_alive()`` and ``join()``).

- Convenience features such as a context manager for pipe handles or timeout
  controls based on ``gevent.Timeout`` are available.

- Any read/write operation on a pipe is ``gevent.lock.Semaphore``-protected
  and therefore greenlet-/threadsafe and atomic.

- gipc obeys `semantic versioning 2 <http://semver.org/>`_.

- Although gipc is in an early development phase, I found it to work very
  stable already. The unit test suite aims to cover all of gipc's features
  within a clean gevent environment. More complex application scenarios,
  however, are not covered so far. Please let me know in which cases
  gipc + gevent fails for you.


.. _installation:

Code, requirements, download, installation
==========================================

Code
----
gipc's Mercurial repository is hosted at
`Bitbucket <https://bitbucket.org/jgehrcke/gipc>`_. It also contains a
changelog and license information.


Requirements
------------

- `gevent <http://gevent.org>`_ >= 1.0 (currently, gipc is tested against
  gevent 1.0rc2). Download recent gevent releases
  `here <https://github.com/SiteSupport/gevent/downloads>`_.
- The unit tests are ensured to pass on CPython 2.6 and 2.7 on Linux as well
  as on Windows.


Download & install via pip
--------------------------

The latest official gipc release from PyPI can be pulled and installed via
`pip <http://www.pip-installer.org>`_::

    $ pip install gipc

pip can also install the current development version of gipc::

    $ pip install hg+https://bitbucket.org/jgehrcke/gipc

Note that the latter requires a recent version of
`distribute <http://packages.python.org/distribute/>`_ which can be installed
by executing
`distribute_setup.py <http://python-distribute.org/distribute_setup.py>`_.

pip is recommended over easy_install. pip installation instructions can be
found `here <http://www.pip-installer.org/en/latest/installing.html>`_.


Install directly via setup.py
-----------------------------

Download and extract the latest gipc release archive from
`PyPI <http://pypi.python.org/pypi/gipc/>`_. Extract it and invoke::

    $ python setup.py install

The same can be done with the latest development version of gipc which
can be downloaded from `Bitbucket <https://bitbucket.org/jgehrcke/gipc>`_.


.. _winnotes:

Notes for Windows users
=======================

- The ``_GIPCReader.get()`` timeout feature is not available.
- "Non-blocking I/O" is imitated by outsourcing blocking I/O calls to threads
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

gipc is written and maintained by
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

Note that these examples are invented with the motivation to demonstrate the API
and capabilities of gipc rather than showing interesting use cases.

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
The read handle ``r`` is provided to the child process. The child invokes
``child_process(r)`` where an endless loop waits for objects on the read end of
the pipe. Upon retrieval, it immediately writes them to stdout.

While child process ``p`` is running, a greenlet ``wg`` is started in the main
process. It executes the function ``writegreenlet`` and passes the write handle
``w`` as an argument. Within this greenlet, one string per second is written to
the write end of the pipe.

After spawning ``wg``, ``p.join()`` is called immediately, i.e. the write
greenlet is running while ``p.join()`` waits for the child process to terminate.
In this state, one message per second is passed between parent and child until a
``KeyboardInterrupt`` exception is raised in the parent.

Upon ``KeyboardInterrupt``, the parent first kills the write greenlet and blocks
cooperatively until it has stopped. Then it terminates the child process (via
``SIGTER`` on Unix) and waits for it to exit via ``p.join()``.


.. _exampleserverclient:

Serving multiple clients (in child) from one server (in parent)
===============================================================

For pure API and reliability demonstration purposes, this example implements TCP
communication between a server in the parent process and multiple clients in
one child process:

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

Output on my test machine: ``1000 clients served within 0.54 s``.

.. _examplesync:

Time-synchronization between processes
======================================

Child process creation may take a significant amount of time, especially on
Windows. This time is not predictable.

When code in the parent should only proceed in the moment the code in the
child has reached a certain state, the proper way to tackle this is a
bidirectional synchronization handshake:

- Process A sends a synchronization request to process B and waits for an
  acknowledgement response. It proceeds upon retrieval.
- Process B sends the acknowledgement in the moment it retrieves the sync
  request and proceeds.

This concept can easily be implemented using a bidirectional ``gipc.pipe()``:

.. code::

    import gevent
    import gipc
    import time


    def main():
        with gipc.pipe(duplex=True) as (cend, pend):
            # `cend` is the channel end for the child, `pend` for the parent.
            p = gipc.start_process(writer_process, args=(cend,))
            # Synchronize with child process.
            pend.put("SYN")
            assert pend.get() == "ACK"
            # Now in sync with child.
            ptime = time.time()
            ctime = pend.get()
            p.join()
            print "Time delta: %.8f s." % abs(ptime - ctime)


    def writer_process(cend):
        with cend:
            assert cend.get() == "SYN"
            cend.put("ACK")
            # Now in sync with parent.
            cend.put(time.time())


    if __name__ == "__main__":
        main()


The marked code blocks in parent and child are entered quasi-simultaneously.
Example output on my test machine (Linux): ``Time delta: 0.00005388 s``. On
Windows, ``time.time()``'s precision is not sufficient to resolve the time
delta (and ``time.clock()`` is not applicable for comparing times across
processes).

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

Creating a pipe and its handle pair
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

.. autoclass:: gipc.gipc._GIPCDuplexHandle()


.. _api_control_childs:

Controlling child processes
===========================

.. autoclass:: gipc.gipc._GProcess()
    :show-inheritance:


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

