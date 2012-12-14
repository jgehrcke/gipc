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

This documentation applies to gipc |release|. It was built on |today|. Sections:

    - :ref:`Introduction (installation, requirements, contact) <introduction>`
    - :ref:`Code examples <examples>`
    - :ref:`API documentation <api>`


.. _introduction:

Introduction
############

What can gipc do for you?
=========================

With ``gipc`` (pronunciation "gipsy") ``multiprocessing.Process``-based child
processes can safely be created anywhere within your ``gevent``-powered
application. Furthermore, ``gipc`` provides gevent-cooperative inter-process
communication.



Isn't this achievable with just gevent+multiprocessing?
=======================================================

Yes, but it requires care: On Unix, child process creation via Python's
``multiprocessing`` package in the context of ``gevent`` might yield an
undesired event loop state in the child and most likely breaks your application
in some way. Furthermore, blocking method calls such as ``join()`` on a
``multiprocessing.Process`` or the ``send()``/``recv()`` methods on a
``multiprocessing.Connection`` are not gevent-cooperative. ``gipc`` overcomes
these challenges for you in a straight-forward fashion and allows for simple
integration of child processes in your application -- on POSIX-compliant
systems as well as on Windows.


Implementation details
======================
- gevent-cooperative communication in ``gipc`` is based on classical anonymous
  pipes. A binary ``pickle`` protocol is used for transmitting
  arbitrary pickleable objects. My test system achieved a payload transfer rate
  of 1200 MB/s and a message transmission rate of 100.000 messages/s through
  one pipe between two processes.

- Child process creation and invocation is done via a thin wrapper around
  ``multiprocessing.Process``. On Unix, the libev event loop is re-initialized
  in the child before execution of the target function.

- On POSIX-compliant systems, gevent-aware child process monitoring is based on
  libev child watchers (this affects ``is_alive()`` and ``join()``).

- Convenience features such as a context manager for pipe handles or timeout
  controls based on ``gevent.Timeout`` are available.

- Any read/write operation on a pipe is ``gevent.lock.Semaphore``-protected
  and therefore greenlet-/threadsafe and atomic.


Installation
============

Via pip
-------

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


Directly via setup.py
---------------------

Download the latest release from `PyPI <http://pypi.python.org/pypi/gipc/>`_. 
Extract the archive and invoke::

    $ python setup.py install

The same can be done with the latest development version of ``gipc`` which 
can be downloaded from `bitbucket <https://bitbucket.org/jgehrcke/gipc>`_.

Once installed, you can remove gipc via ``pip uninstall gipc`` or manually.


Requirements
============

- gevent >= 1.0 (tested against gevent 1.0rc2). Download gevent 
  `here <https://github.com/SiteSupport/gevent/downloads>`_.
- unit tests pass on Python 2.6 and 2.7


Notes for Windows users
=======================

- The ``get()`` timeout feature is not available.
- Non-blocking I/O is faked via gevent threadpool, leading to a significant
  messaging performance drop compared to POSIX-compliant systems.

The optimal solution to both problems would be IOCP-based. Maybe one day
gevent is `libuv <https://github.com/joyent/libuv>`_-backed, which uses
IOCP on Windows and would allow for running the same gevent code on Windows 
as on POSIX-based systems. Furthermore, if gevent went with libuv, the
strengths of both, the node.js and the gevent worlds woud be merged.
Denis, the maintainer of gevent,  seems to be
`open <https://twitter.com/gevent/status/251870755187478529>`_ to such a
transition and the first steps are already
`done <https://github.com/saghul/uvent>`_.


Usage
=====

See :ref:`examples <examples>` and :ref:`API <api>` sections.



Author, license, contact
========================

``gipc`` is written and maintained by 
`Jan-Philip Gehrcke <http://gehrcke.de>`_ and is licensed under the 
`Apache License 2.0 <http://www.apache.org/licenses/LICENSE-2.0.txt>`_. 
Your feedback is highly appreciated. You can contact me at 
jgehrcke@googlemail.com.


.. _examples:

Examples
########

- :ref:`example1`
- :ref:`example2`


.. _example1:

Infinite messaging from greenlet in parent to child
===================================================

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

The context manager ``with gipc.pipe() as (r, w)`` creates a pipe with read handle ``r`` and write handle ``w``. On context exit (latest) the pipe ends will be closed properly.

Within the context, a child process is spawned via ``gipc.start_process()``. The read handle ``r`` is provided to the child which calls ``child_process(r)`` where an endless loop waits for messages/objects on the read end of the pipe and immediately prints those upon retrieval.

While the child process ``p`` runs, a greenlet ``wg`` has been started in the main process. It executes the function ``writegreenlet`` while providing ``w`` as an argument. Within this greenlet, one string per second is written into the write end of the pipe.

After spawning ``wg``, ``p.join()`` is called immediately, i.e. the write greenlet is executed concurrently with ``p.join()``. In this state, messages are passed between parent and child until the parent raises the ``KeyboardInterrupt`` exception.

On ``KeyboardInterrupt``, the parent first kills the write greenlet and blocks cooperatively until it has stopped. Secondly, it tries to terminate the child process (via ``SIGTER`` on Unix) and waits for it to exit via ``p.join()``.


.. _example2:

Time-synchronized messaging between processes
=============================================

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
            for i in xrange(1000):
                writer.put("A" * 1000)
            writer.put('STOP')


    if __name__ == "__main__":
        main()



.. _api:

gipc API
########


Spawning child processes
========================

.. automodule:: gipc
    :members: start_process


Creating a pipe and its handle-pair
===================================

.. automodule:: gipc
   :members: pipe


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


Controlling child processes
===========================

.. autoclass:: gipc.gipc._GProcess()
    :show-inheritance:
    :members: join


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

