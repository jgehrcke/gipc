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
