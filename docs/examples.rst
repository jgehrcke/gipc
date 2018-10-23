.. _examples:

********
Examples
********
This section shows three example programs using gipc. These examples have been
created mainly for educational purposes and might therefore lack real-world
purpose :-). I hope they are useful!

The latest version of these examples can be found `on GitHub
<https://github.com/jgehrcke/gipc>`_ (that code there is also run as part of CI
and contains a few consolidations for platforms like Windows and mac OS which
are left out in the snippets below).

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
