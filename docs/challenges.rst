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
kill greenlets or watchers one by one. Is that a memory leak? This indeed
accumulates a little bit of uncollectable garbage for every newly generated
process generation in the hierarchy. However, this should only be a problem when
the application grows the process hierarchy arbitrarily deep over time, i.e.
when a child process starts a child process which starts a child process, ...,
in an unbounded fashion. If you don't do that it's fine.

On POSIX-compliant systems gipc entirely avoids multiprocessing's child
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
