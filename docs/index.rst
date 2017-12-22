.. gipc documentation master file
   Copyright 2012-2017 Jan-Philip Gehrcke. See LICENSE file for details.

.. |br| raw:: html

   <br />

.. |space| raw:: html

   &nbsp;&nbsp;

.. toctree::
    :maxdepth: 2

########################################
gipc: child processes and IPC for gevent
########################################

.. rst-class:: byline

    `GitHub <https://github.com/jgehrcke/gipc>`_ |space| | |space|
    `PyPI <https://pypi.python.org/pypi/gipc>`_ |br|
    An open source software project created by
    `Jan-Philip Gehrcke <https://gehrcke.de>`_

.. raw:: html

   <hr />

gipc (pronunciation as in “gipsy”) provides reliable child process management
and inter-process communication in the context of `gevent
<https://github.com/gevent/gevent>`_.

gipc works on CPython 2.7/3.4/3.5/3.6. It requires gevent 1.2 and supports both,
Unix-like systems as well as Windows. On Unix-like systems, gipc also runs on
PyPy2.7 and PyPy3.

This documentation applies to gipc |release|. It was built on |today|.

**Overview**

Direct usage of Python's `multiprocessing package
<https://docs.python.org/3/library/multiprocessing.html>`_ in the context of a
gevent-powered application is error-prone and may break the application in
various subtle ways (see :ref:`below <challenges>`).

With gipc, ``multiprocessing.Process``-based child processes can safely be
created anywhere within your gevent-powered application. The API of
``multiprocessing.Process`` objects is provided in a gevent-cooperative fashion.
Also, gipc provides a pipe-based transport layer for gevent-cooperative
inter-greenlet and inter-process communication. gipc is lightweight and easy to
integrate.

gipc is happily used by, among others,
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


**Contents of this documentation:**

    - :ref:`Usage <usage>`
    - :ref:`Which problem does gipc address, specifically? <what>`
    - :ref:`Architecture notes <archnotes>`
    - :ref:`Is gipc reliable? <reliable>`
    - :ref:`Download & installation <installation>`
    - :ref:`Platform support <platforms>`
    - :ref:`Notes for Windows users <winnotes>`
    - :ref:`Author, license, contact <contact>`
    - :ref:`Code examples <examples>`
    - :ref:`API documentation <api>`
        - :ref:`Spawning child processes <api_spawn>`
        - :ref:`Creating a pipe and its handle-pair <api_pipe_create>`
        - :ref:`Handling handles <api_handles>`
        - :ref:`Controlling child processes <api_control_childs>`
        - :ref:`Exception types <api_exceptions>`


.. _usage:

*****
Usage
*****
gipc's interface is slim. All you will probably interact with are
``gipc.start_process()``, ``gipc.pipe()``, and their returned objects. Make
yourself familiar with gipc's behavior by going through the code
:ref:`examples <examples>` as well as through the :ref:`API <api>` section.


Quick-start example
===================
The following example program uses gipc for spawning a child process and for
creating a pipe. The pipe has a read end and a write end. The program sends a
dummy Python object (the integer 0 in this case) from a greenlet in the main
(parent) process through the pipe to the child process::

    import gevent
    import gipc

    def writelet(w):
        # This function runs as a greenlet in the parent process.
        # Put a Python object into the write end of the pipe.
        w.put(0)


    def readchild(r):
        # This function runs in a child process.
        # Read object from the read end of the pipe and confirm that it is the
        # expected one.
        assert r.get() == 0


    def main():
        with gipc.pipe() as (readend, writeend):
            # Start 'writer' greenlet. Provide it with the pipe write end.
            g = gevent.spawn(writelet, writeend)
            # Start 'reader' child process. Provide it with the pipe read end.
            p = gipc.start_process(target=readchild, args=(readend,))
            # Wait for both to finish.
            g.join()
            p.join()


    # Protect entry point from being executed upon import (this matters
    # on Windows).
    if __name__ == "__main__":
        main()

Although quite simple, this code would have various unwanted side-effects if
used with the canonical multiprocessing API instead of ``gipc.start_process()``
and ``gipc.pipe()``. These side effects are described below in the
:ref:`Challenges <challenges>` section.


.. _what:

**********************************************
When would you want to use gipc, specifically?
**********************************************
There is plenty of motivation for using multiple processes in event-driven
architectures. The rationale behind gipc is that applying multiple processes
that communicate among each other can be a decent solution for various types of
"concurrency problems". It helps decoupling system components by making each
process responsible for just one architectural aspect ("separation of
concerns"). Furthermore, even a generally I/O-intense application can at some
point become CPU-bound in which case the distribution of tasks across multiple
loosely coupled processes is a way to make efficient use of multi-core machine
architectures and to easily increase application performance.

The canonical way for running Python code in multiple processes in a Python
application is to use ``multiprocessing`` from Python's standard library.
However, usage of this package within a gevent-powered application usually
breaks the application in various non-obvious ways (see :ref:`next section
<challenges>`). gipc is developed with the motivation to solve these issues
transparently and to make using gevent in combination with multiprocessing-based
child processes and inter-process communication (IPC) a no-brainer again:

- With gipc, ``multiprocessing.Process``-based child processes can safely be
  created and monitored anywhere within your gevent-powered application.
  Non-obvious side-effects of child process creation in the context of gevent
  are prevented.
- The API of ``multiprocessing.Process`` objects is provided in a
  gevent-cooperative fashion.
- gevent natively works in children.
- gipc provides a pipe-based transport layer for gevent-cooperative IPC so that
  application developers can easily make greenlets exchange information in a
  stream-like fashion; across process boundaries or within a process.
- gipc is lightweight and simple to integrate, really!


.. _challenges:

****************************************************
What are the challenges and what is gipc's solution?
****************************************************
Depending on the operating system in use, the creation of child processes via
Python's multiprocessing in the context of a gevent application requires special
treatment. Most care is required on POSIX-compliant systems: greenlets spawned
in the current process before forking obviously become cloned by ``fork()`` and
haunt in the child process, which usually is undesired behavior. The following
code snippet clarifies this behavior by implementing the example from above, but
this time by directly using multiprocessing instead of gipc (this has been
tested on Linux with Python 3.4 & gevent 1.1)::

    import gevent
    import multiprocessing

    def writelet(c):
        c.send(0)

    def readchild(c):
        gevent.sleep(0)
        assert c.recv() == 0
        assert c.recv() == 0

    if __name__ == "__main__":
        c1, c2 = multiprocessing.Pipe()
        g = gevent.spawn(writelet, c1)
        p = multiprocessing.Process(target=readchild, args=(c2,))
        p.start()
        g.join()
        p.join()

It runs without raising an Exception. Although the code intends to send only one
message to the child through a multiprocessing ``Pipe``, the two ``assert``
statements verify that the child actually receives the same message **twice**.
One message is sent -- as intended -- from the writelet in the parent through
the ``c1`` end of the pipe. It is retrieved at the ``c2`` end of the pipe in the
child. The other message is sent from the spooky writelet clone in the child. It
is also written to the ``c1`` end of the pipe which has implicitly been
duplicated during forking. Greenlet clones in the child of course only run when
a context switch is triggered; in this case via ``gevent.sleep(0)``. As you can
imagine, this behavior may lead to a wide range of side-effects including race
conditions, and therefore almost guarantees especially tedious debugging
sessions.

The second class of serious issues in the code above is that it contains several
non-cooperatively blocking function calls: ``p.join()`` as well as the
``send()``/``recv()`` calls (of ``multiprocessing.Connection`` objects) block
the calling greenlet non-cooperatively, i.e. they do not allow for a context
switch into other greenlets. While this does not lead to an error in the simple
example code above, this behavior is not tolerable in real-world gevent
applications.

**Solution:**

gipc overcomes these and other issues transparently and in a rather
straight-forward fashion:

The most basic design assumption behind gipc is that application developers
never actually want to duplicate all currently running greenlets upon fork. This
leads to the rational of first destroying the inherited "gevent state" in the
child and then creating a fresh gevent context, before invoking the target
function.

The goal is that each child process invoked via gipc starts off with a fresh
gevent state before entering the user-given target function. Correspondingly, as
one of the first actions, a child process created via gipc destroys the
inherited gevent hub as well as the inherited libev event loop and constructs
its own fresh versions of both. This way, inherited greenlets as well as libev
watchers effectively become *orphaned* -- the fresh hub and event loop are not
related to them anymore. The new gevent hub never context-switches into the old
inherited greelets which reliably prevents any further code execution from
happening. Also, libev event loop destruction disables inherited libev watchers
and associated callbacks from firing. After all, this technique effectively
disables all inherited gevent and libev magic without the need to deconstruct or
kill greenlets or watchers one by one (this indeed accumulates uncollectable
garbage for every newly generated process generation in the hierarchy, and an
application using gipc should not grow the hierarchy arbitrarily deep over
time).

On POSIX-compliant systems, gipc entirely avoids multiprocessing's child
monitoring implementation (which is based on the class of ``wait`` system calls)
and instead uses libev's wonderful child watcher system (based on SIGCHLD signal
transmission), enabling gevent-cooperative waiting for child process termination
(that is how ``p.join()`` from the example above can be made cooperative).

For implementing gevent-cooperative inter-process communication, gipc uses
efficient pipe-based data transport channels with *non-blocking* I/O system
calls. gipc's transport channel system has been carefully designed: for
instance, it takes care of closing dispensable file descriptors in the parent as
well as in the child after forking and also abstracts away the difficulties of
passing pipe handles between processes on Windows. gipc also abstracts away the
implementation differences of the multiprocessing package between Python 2 and
3.

Overall, gipc's main goal is to allow for the integration of child processes in
your gevent-powered application via a simple API -- no matter if you are running
Python 2 or Python 3, Windows, or a Unix-like system such as Linux or Darwin.


.. _archnotes:

*********************************
gipc's architecture in a nutshell
*********************************
- Child process creation and invocation is done via a thin wrapper around
  ``multiprocessing.Process``. On Unix-like systems, the inherited gevent hub as
  well as the inherited libev event loop become destroyed and re-initialized in
  the child before execution of the user-given target function.

- On Unix-like systems, gevent-cooperative child process monitoring is
  implemented with libev child watchers which rely on SIGCHLD signal
  transmission.

- gipc uses anonymous pipes as a stream-like transport layer for
  gevent-cooperative communication between greenlets within the same process or
  across process boundaries. By default, a binary ``pickle`` protocol is used
  which allows for transmitting arbitrary Python objects. Reading and writing on
  pipes is done with ``gevent``'s cooperative versions of ``os.read()`` and
  ``os.write()`` (on Unix-like systems they use non-blocking I/O, whereas on
  Windows a thread pool is used for emulating that behavior). On Linux, my test
  system (Xeon E5630) achieved a payload transfer rate of 1200 MB/s and a
  message transmission rate of 100.000 messages/s through one pipe between two
  processes.

- gipc automatically closes pipe handles in the parent process after being
  passed to the child, and also closes those in the child that were not
  explicitly transferred to it. This auto-close behavior might be a limitation
  in certain special cases. However, it automatically prevents file descriptor
  leakage and forces developers to make deliberate choices about which handles
  should be transferred explicitly.

- gipc provides convenience features such as a context manager for pipe
  handles or timeout controls based on ``gevent.Timeout``.

- Read/write operations on a pipe are ``gevent.lock.Semaphore``-protected
  and therefore greenthread-safe.


.. _reliable:

*****************
Is gipc reliable?
*****************
gipc is developed with a strong focus on reliability and with best intentions in
mind. Although gipc handles a delicate combination of signals, threads, and
forking, I have observed it to work reliably. The unit test suite covers all of
gipc's features within a clean gevent environment, but also covers scenarios of
medium complexity. To my knowledge, gipc is being deployed in serious production
scenarios.

But still, generally, you should be aware of the fact that mixing any of fork,
threads, greenlets and an event loop library such as libev bears the potential
for various kinds of corner-case disasters. One could argue that ``fork()`` in
the context of libev without doing a clean ``exec`` in the child already *is*
broken design. However, many people would like to do exactly this and gipc's
basic approach has proven to work in such cases. Now it is up to you
to evaluate gipc in the context of your project -- please share your experience.


.. _installation:

***********************
Download & installation
***********************
The latest gipc release from PyPI can be downloaded and installed via
`pip <https://pip.pypa.io/en/stable/>`_::

    $ pip install gipc

pip can also install the current development version of gipc::

    $ pip install git+https://github.com/jgehrcke/gipc

gipc obeys `semantic versioning <http://semver.org/>`_.


.. _platforms:

****************
Platform support
****************
The current version of gipc works on CPython 2.7/3.4/3.5/3.6. It has been tested
against gevent 1.2 and supports both, Unix-like systems as well as Windows. On
Unix-like systems, gipc also works with PyPy2.7 and PyPy3. Tests are not
automatically run for the Windows and Darwin platforms and corresponding
community feedback is greatly appreciated.


.. _winnotes:

***********************
Notes for Windows users
***********************
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

************************
Author, license, contact
************************
gipc is written and maintained by
`Jan-Philip Gehrcke`_ and licensed under an MIT license
(see LICENSE file for details). Your feedback is highly appreciated. You can
contact me at jgehrcke@googlemail.com or use the
`Bitbucket issue tracker <https://bitbucket.org/jgehrcke/gipc/issues>`_.


.. _examples:

********
Examples
********
The following examples are meant to demonstrate the API and capabilities of
gipc, rather than showing interesting use cases. I hope they are useful!

- :ref:`exampleipc`
- :ref:`exampleserverclient`
- :ref:`examplesync`

.. _exampleipc:

Example 1: gipc.pipe()-based messaging from greenlet in parent to child
=======================================================================

Pretty basic gevent and gipc concepts are explained by means of the following
messaging example:

.. code-block:: python

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
handle ``r`` and write handle ``w``. On context exit (latest) the pipe ends
will be closed properly.

After creating the pipe context, the above code spawns a child process via
``gipc.start_process()``. The child process is instructed to execute the target
function named ``child_process`` whereas the pipe read handle ``r`` is provided
as an argument to this target function. Within ``child_process()`` an endless
loop waits for objects on the read end of the pipe via the cooperatively
blocking call to ``reader.get()``. Upon retrieval, it immediately writes their
string representation to stdout.

After invocation of the child process (represented by an object bound to
name ``p``), a greenlet ``wg`` is spawned within the main process. This
greenlet executes the function ``writegreenlet``, whereas the pipe write handle
``w`` is provided as an argument. Within this greenlet, one string per second
is written to the write end of the pipe.

After spawning ``wg``, ``p.join()`` is called immediately in the parent
process. ``p.join()`` is blocking cooperatively, i.e. it allows for a context
switch into the write greenlet (this actually is the magic behind
gevent/greenlets). Hence, the write greenlet is 'running' while ``p.join()``
cooperatively waits for the child process to terminate. The write greenlet
spends most of its time in ``gevent.sleep()``, which is also blocking
cooperatively, allowing for context switches back to the main greenlet in the
parent process, which is executing ``p.join()``. In this state, one message per
second is passed between parent and child until a ``KeyboardInterrupt``
exception is raised in the parent.

Upon ``KeyboardInterrupt``, the parent first kills the write greenlet and blocks
cooperatively until it has stopped. Then it terminates the child process (via
``SIGTER`` on Unix) and waits for it to exit via ``p.join()``.


.. _exampleserverclient:

Example 2: serving multiple clients (in child) from one server (in parent)
==========================================================================

For pure API and reliability demonstration purposes, this example implements
TCP communication between a server in the parent process and multiple clients
in one child process:

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

.. code-block:: python

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

Example 3: time-synchronization between processes
=================================================

Child process creation may take a significant amount of time, especially on
Windows. The exact amount of time is not predictable.

When code in the parent should only proceed in the moment the code in the
child has reached a certain state, the proper way to tackle this is a
bidirectional synchronization handshake:

- Process A sends a synchronization request to process B and waits for an
  acknowledgment response. It proceeds upon retrieval.
- Process B sends the acknowledgment in the moment it retrieves the sync
  request and proceeds.

This concept can easily be implemented using a bidirectional ``gipc.pipe()``:

.. code-block:: python

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

********
gipc API
********

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
