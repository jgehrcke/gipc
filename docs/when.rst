.. _when:

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
loosely or tightly coupled processes is a way to make efficient use of
multi-core machine architectures and to easily increase application performance.

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
