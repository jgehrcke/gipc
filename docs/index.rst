.. gipc documentation master file, created by
   sphinx-quickstart on Thu Nov 22 15:14:51 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
    :hidden:
    :maxdepth: 2

========================================
GIPC: Multiprocessing and IPC for gevent
========================================

This documentation applies to gipc |release|. It was built on |today|. Sections:

    - :ref:`introduction`
    - :ref:`examples`
    - :ref:`api`


.. _introduction:

Introduction
############

What can gipc do for you?
=========================

With ``gipc`` you can easily use ``multiprocessing`` and ``gevent`` within one
Python application. It provides

- gevent-aware ``multiprocessing.Process``-based child processes.
- gevent-cooperative inter-process communication.



Isn't this achievable with just gevent+multiprocessing?
=======================================================

Yes, but it requires some care: On Unix, child process creation via Python's
``multiprocessing`` package in the context of ``gevent`` might yield an
undesired event loop state in the child and most likely breaks your application
in some way. Furthermore, blocking method calls such as ``join()`` on a
``multiprocessing.Process`` or the ``send()``/``recv()`` methods on a
``multiprocessing.Connection`` are not gevent-cooperative. ``gipc`` overcomes
these challenges  for you in a straight-forward fashion and allows for simple
integration of child processes in your application.


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

- gevent >= 1.0 (tested against gevent 1.0rc2). Download gevent `here <https://github.com/SiteSupport/gevent/downloads>`_.
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

See :ref:`examples` and :ref:`api` sections.



Author, license, contact
========================

``gipc`` is written and maintained by `Jan-Philip Gehrcke <http://gehrcke.de>`_ and is licensed under the `Apache License 2.0 <http://www.apache.org/licenses/LICENSE-2.0.txt>`_. Your feedback is highly appreciated. You can contact me at jgehrcke@googlemail.com.


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
                writer.put("A"*1000)
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

