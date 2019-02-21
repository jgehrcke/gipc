# -*- coding: utf-8 -*-
# Copyright 2012-2018 Dr. Jan-Philip Gehrcke. See LICENSE file for details.


"""
gipc unit tests, written for py.test.

py.test runs tests by order of definition. This is useful for running simple,
fundamental tests first and more complex tests later.
"""


import os
import sys
import time
import signal
import random
import logging
import multiprocessing


import gevent
import gevent.queue
sys.path.insert(0, os.path.abspath('..'))
from gipc import start_process, pipe, GIPCError, GIPCClosed, GIPCLocked
from gipc.gipc import _get_all_handles as get_all_handles
from gipc.gipc import _set_all_handles as set_all_handles
from gipc.gipc import _signals_to_reset as signals_to_reset


from py.test import raises, mark


logging.basicConfig(
    format='%(asctime)s,%(msecs)-6.1f [%(process)-5d]%(funcName)s# %(message)s',
    datefmt='%H:%M:%S')
log = logging.getLogger()
log.setLevel(logging.DEBUG)


WINDOWS = sys.platform == "win32"
LONG = 999999
SHORTTIME = 0.01
ALMOSTZERO = 0.00001
LONGERTHANBUFFER = "A" * 9999999


def check_for_handles_left_open():
    """Frequently used during test teardown.

    Raise exception if test case left open some file descriptor. Perform
    rigorous close attempts in order to make sure to not leak file descriptors
    during tests.
    """
    handles = get_all_handles()
    if handles:
        for h in handles:
            try:
                h.close()
                os.close(h._fd)
            except (OSError, GIPCError, TypeError):
                pass
        set_all_handles([])
        raise Exception("Test case left open descriptor behind.")


class TestComm(object):
    """Test basic communication within single greenlets or among greenlets via
    pipe-based unidirectional transport channels and `_GIPCHandle`s.

    Flow for each test_method:
        o = TestClass()
        o.setup()
        try:
            o.test_method()
        finally:
            o.teardown()
    """
    def setup(self):
        # Create one pipe & two handles for each test case.
        self.rh, self.wh = pipe()

    def teardown(self):
        # Test cases must not close handles themselves.
        self.rh.close()
        self.wh.close()
        check_for_handles_left_open()

    def test_singlemsg_short_bin(self):
        m = "OK"
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self.wh.put(m)
        t = g.get()
        assert m == t

    def test_singlemsg_short_list(self):
        m = [1]
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self.wh.put(m)
        t = g.get()
        assert m == t

    def test_singlemsg_short_list_commontypes(self):
        mlist = [1, True, False, None, Exception]
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self.wh.put(mlist)
        tlist = g.get()
        for i, m in enumerate(mlist):
            assert m == tlist[i]

    def test_singlemsg_long_bin(self):
        m = "OK" * LONG
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self.wh.put(m)
        assert m == g.get()

    def test_singlemsg_long_list(self):
        m = [1] * LONG
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self.wh.put(m)
        assert m == g.get()

    def test_singlemsg_between_greenlets(self):
        m = [1] * LONG
        def gwrite(writer, m):
            writer.put(m)
        def gread(reader):
            return reader.get()
        gw = gevent.spawn(gwrite, self.wh, m)
        gr = gevent.spawn(gread, self.rh)
        assert m == gr.get()
        gw.get()

    def test_onewriter_two_readers(self):
        m = [1] * LONG
        def gwrite(writer, m):
            writer.put(m)
            writer.put(m)
        def gread(reader):
            return reader.get()
        gw = gevent.spawn(gwrite, self.wh, m)
        gr1 = gevent.spawn(gread, self.rh)
        gr2 = gevent.spawn(gread, self.rh)
        assert m == gr1.get() == gr2.get()
        gw.get()

    def test_twowriters_one_reader(self):
        m = [1] * LONG
        def gwrite(writer, m):
            writer.put(m)
        def gread(reader):
            return [reader.get() for _ in range(2)]
        gw1 = gevent.spawn(gwrite, self.wh, m)
        gw2 = gevent.spawn(gwrite, self.wh, m)
        gr = gevent.spawn(gread, self.rh)
        assert [m, m] == gr.get()
        gw1.get()
        gw2.get()

    def test_all_handles_length(self):
        assert len(get_all_handles()) == 2


class TestClose(object):
    """Test `_GIPCHandle`s close behavior and read/write behavior in context of
    closing.
    """
    def setup(self):
        self.rh, self.wh = pipe()

    def teardown(self):
        # Each test case needs to properly close both handles.
        check_for_handles_left_open()

    def test_twoclose(self):
        self.wh.close()
        with raises(GIPCClosed):
            self.wh.close()
        self.rh.close()

    def test_closewrite(self):
        self.wh.close()
        with raises(GIPCClosed):
            self.wh.put('')
        self.rh.close()

    def test_closeread(self):
        self.rh.close()
        with raises(GIPCClosed):
            self.rh.get()
        self.wh.close()

    def test_readclose_whileread(self):
        g = gevent.spawn(lambda r: r.get(), self.rh)
        gevent.sleep(SHORTTIME)
        with raises(GIPCLocked):
            self.rh.close()
        g.kill()
        self.wh.close()
        self.rh.close()

    def test_closewrite_read(self):
        self.wh.close()
        with raises(EOFError):
            self.rh.get()
        self.rh.close()

    def test_closeread_write(self):
        self.rh.close()
        with raises(OSError):
            self.wh.put('')
        self.wh.close()

    def test_write_closewrite_read(self):
        self.wh.put("a")
        self.wh.close()
        assert self.rh.get() == "a"
        with raises(EOFError):
            self.rh.get()
        self.rh.close()


class TestProcess(object):
    """Test child process behavior and `_GProcess` API.
    """
    def test_is_alive_true(self):
        p = start_process(p_child_a)
        assert p.is_alive()
        p.join()
        assert p.exitcode == 0

    def test_is_alive_false(self):
        p = start_process(p_child_a)
        p.join()
        assert not p.is_alive()
        assert p.exitcode == 0

    def test_exitcode_0(self):
        p = start_process(p_child_a)
        p.join()
        assert p.exitcode == 0

    def test_exitcode_sigkill(self):
        p = start_process(p_child_b)
        p.join()
        if not WINDOWS:
            assert p.exitcode == -signal.SIGKILL
        else:
            assert p.exitcode == 1

    def test_exitcode_1(self):
        p = start_process(p_child_c)
        p.join()
        assert p.exitcode == 1

    def test_pid(self):
        p = start_process(p_child_a)
        p.join()
        assert p.pid is not None
        assert p.exitcode == 0

    def test_terminate(self):
        p = start_process(gevent.sleep, args=(1,))
        # Test __repr__ and __str__
        p.__repr__()
        p.terminate()
        p.join()
        p.__repr__()
        assert p.exitcode == -signal.SIGTERM

    def test_child_in_child_in_child(self):
        p = start_process(p_child_e)
        p.join()

    def test_join_timeout(self):
        p = start_process(gevent.sleep, args=(0.1, ))
        p.join(ALMOSTZERO)
        assert p.is_alive()
        p.join()
        assert p.exitcode == 0

    def test_typecheck_args(self):
        with raises(TypeError):
            start_process(gevent.sleep, args="peter")

    def test_typecheck_kwargs(self):
        with raises(TypeError):
            start_process(gevent.sleep, kwargs="peter")

    @mark.skipif('WINDOWS')
    def test_exitcode_previous_to_join(self):
        p = start_process(lambda: gevent.sleep(SHORTTIME))
        # Assume that the child process is still alive when the next
        # line is executed by the interpreter (there is no guarantee
        # for that, but it's rather likely).
        assert p.exitcode is None

        # Expect the child watcher mechanism to pick up
        # and process the child process termination event
        # (within at most two seconds). The `gevent.sleep()`
        # invocations allow for libev event loop iterations,
        # two of which are required after the OS delivers the
        # SIGCHLD signal to the parent process: one iteration
        # invokes the child reap loop, and the next invokes
        # the libev callback associated with the termination
        # event.
        deadline = time.time() + 2
        while time.time() < deadline:
            if p.exitcode is not None:
                assert p.exitcode == 0
                p.join()
                return
            gevent.sleep(ALMOSTZERO)
        raise Exception('Child termination not detected')


def p_child_a():
    gevent.sleep(SHORTTIME)


def p_child_b():
    if not WINDOWS:
        os.kill(os.getpid(), signal.SIGKILL)
    else:
        sys.exit(1)


def p_child_c():
    sys.exit(1)


def p_child_e():
    i = start_process(p_child_e2)
    i.join()


def p_child_e2():
    ii = start_process(p_child_e3)
    ii.join()


def p_child_e3():
    pass


class TestIPC(object):
    """Test file descriptor passing and inter-process communication based on
    unidirectional message transfer channels.
    """
    def setup(self):
        self.rh, self.wh = pipe()
        self.rh2, self.wh2 = pipe()

    def teardown(self):
        # Each test case needs to properly have closed all 4 handles in parent.
        check_for_handles_left_open()

    def test_handlecount(self):
        p = start_process(ipc_handlecounter1, args=(self.rh, self.rh2))
        p.join()
        assert p.exitcode == 0
        # After passing two handles to the child, only 2 must be left open.
        assert len(get_all_handles()) == 2
        self.wh.close()
        self.wh2.close()

    def test_singlemsg_long_list(self):
        m = [1] * LONG
        p = start_process(ipc_readchild, args=(self.rh, m))
        self.wh.put(m)
        p.join()
        assert p.exitcode == 0
        with raises(GIPCClosed):
            self.rh.close()
        self.rh2.close()
        self.wh.close()
        self.wh2.close()

    def test_twochannels_singlemsg(self):
        m1 = "OK"
        m2 = "FOO"
        p = start_process(ipc_child_b, args=(self.rh, self.rh2, m1, m2))
        self.wh.put(m1)
        self.wh2.put(m2)
        p.join()
        assert p.exitcode == 0
        self.wh.close()
        self.wh2.close()

    def test_childparentcomm_withinchildcomm(self):
        m1 = "OK"
        m2 = "FOO"
        p = start_process(
            target=ipc_child_c, args=(self.rh, self.rh2, m1, m2))
        self.wh.put(m1)
        self.wh2.put(m2)
        p.join()
        assert p.exitcode == 0
        self.wh.close()
        self.wh2.close()

    def test_childchildcomm(self):
        m = {("KLADUSCH",): "foo"}
        pr = start_process(ipc_readchild, args=(self.rh, m))
        pw = start_process(ipc_writechild, args=(self.wh, m))
        pr.join()
        pw.join()
        assert pr.exitcode == 0
        assert pw.exitcode == 0
        self.rh2.close()
        self.wh2.close()

    def test_handler_after_transfer_to_child(self):
        p = start_process(ipc_child_boring_reader, args=(self.rh,))
        with raises(GIPCClosed):
            self.rh.close()
        p.join()
        assert p.exitcode == 0
        self.rh2.close()
        self.wh.close()
        self.wh2.close()

    def test_handler_in_nonregistered_process(self):
        p = multiprocessing.Process(target=ipc_child_d, args=(self.rh, ))
        p.start()
        p.join()
        if not WINDOWS:
            # On POSIX-compliant systems, gipc disables multiprocessing's
            # capability to monitor child states.
            assert p.exitcode is None
        else:
            assert p.exitcode == 0
        self.rh.close()
        self.rh2.close()
        self.wh.close()
        self.wh2.close()

    def test_child_in_child_in_child_comm(self):
        m = "RATZEPENG"
        p = start_process(ipc_child_f, args=(self.wh, m))
        p.join()
        assert m == self.rh.get()
        assert p.exitcode == 0
        self.rh.close()
        self.rh2.close()
        self.wh2.close()

    def test_early_readchild_exit(self):
        start_process(ipc_readonce_then_exit, (self.rh,))
        # The first message sent is read by the reading child. The child
        # then exits and implicitly closes the read end of the pipe. The
        # following write attempt should result in an exception raised in the
        # writing process (the initial one): OSError: [Errno 32] Broken pipe
        # This only happens if SIGPIPE is ignored (otherwise, if SIGPIPE
        # is not ignored and not handled, the writing process exits silently
        # with code -13 on POSIX).
        with raises(OSError) as excinfo:
            while True:
                self.wh.put(0)
        if not WINDOWS:
            assert "Broken pipe" in str(excinfo.value)
        else:
            assert "Invalid argument" in str(excinfo.value)
        self.wh.close()
        self.rh2.close()
        self.wh2.close()

    def test_early_readchild_exit_write_from_child(self):
        pr = start_process(ipc_readonce_then_exit, (self.rh,))
        pw = start_process(ipc_endless_write_for_early_reader_exit, (self.wh,))
        # This test is to make sure equivalent behavior as in test
        # `test_early_readchild_exit` when the writing process is a
        # child process itself (above, the write process in the initial
        # process). Since gipc's child process creation
        # routine messes around with signal handlers, this test makes
        # sure that SIGPIPE is ignored in the child and that a
        # failing write attempt (after early read child exit) results
        # in an exception raised in the writing process.
        pr.join()
        pw.join()
        assert pr.exitcode == 0
        assert pw.exitcode == 0
        self.rh2.close()
        self.wh2.close()


def ipc_readonce_then_exit(r):
    r.get()


def ipc_endless_write_for_early_reader_exit(w):
    with raises(OSError) as excinfo:
        while True:
            w.put(0)
    if not WINDOWS:
        assert "Broken pipe" in str(excinfo.value)
    else:
        assert "Invalid argument" in str(excinfo.value)


def ipc_handlecounter1(r1, r2):
    assert len(get_all_handles()) == 2


def ipc_readchild(r, m):
    assert r.get() == m


def ipc_writechild(w, m):
    w.put(m)


def ipc_child_boring_reader(r):
    pass


def ipc_child_b(r1, r2, m1, m2):
    assert r1.get() == m1
    assert r2.get() == m2


def ipc_child_c(r1, r2, m1, m2):
    assert r1.get() == m1
    # Test messaging between greenlets in child.
    local_reader, local_writer = pipe()
    testmsg = [1] * LONG
    gw = gevent.spawn(lambda w: w.put(testmsg), local_writer)
    gr = gevent.spawn(lambda r: r.get(), local_reader)
    assert testmsg == gr.get()
    gr.get()
    gw.get()
    local_reader.close()
    local_writer.close()
    # Receive second message from parent.
    assert r2.get() == m2


def ipc_child_d(r):
    with raises(GIPCError):
        r.close()


def ipc_child_f(w, m):
    assert len(get_all_handles()) == 1
    i = start_process(ipc_child_f2, args=(w, m))
    i.join()
    assert i.exitcode == 0
    with raises(GIPCClosed):
        w.close()


def ipc_child_f2(w, m):
    ii = start_process(ipc_child_f3, args=(w, m))
    ii.join()
    assert ii.exitcode == 0


def ipc_child_f3(w, m):
    w.put(m)
    w.close()


class TestContextManager(object):
    """Test context manager behavior regarding unidirectional transport.
    """
    def teardown(self):
        check_for_handles_left_open()

    def test_combi(self):
        with pipe() as (r, w):
            fd1 = r._fd
            fd2 = w._fd
        with raises(OSError):
            os.close(fd1)
        with raises(OSError):
            os.close(fd2)

    def test_single_reader(self):
        r, w = pipe()
        with w as foo:
            fd = foo._fd
        with raises(OSError):
            os.close(fd)
        assert len(get_all_handles()) == 1
        with raises(GIPCClosed):
            w.close()
        r.close()

    def test_single_writer(self):
        r, w = pipe()
        with r as foo:
            fd = foo._fd
        with raises(OSError):
            os.close(fd)
        assert len(get_all_handles()) == 1
        with raises(GIPCClosed):
            r.close()
        w.close()

    def test_close_in_context(self):
        with pipe() as (r, w):
            w.put('')
            r.get()
            r.close()
            w.close()

    def test_lock_out_of_context_single(self):
        r, w = pipe()
        g = gevent.spawn(lambda r: r.get(), r)
        gevent.sleep(SHORTTIME)
        with raises(GIPCLocked):
            with r:
                pass
                # The context manager can't close `r`, as it is locked in `g`.
        g.kill(block=False)
        # Ensure killing via 'context switch', i.e. yield control to other
        # coroutines (otherwise the subsequent close attempt will fail with
        # `GIPCLocked` error).
        gevent.sleep(-1)
        # Close writer first. otherwise, `os.close(r._fd)` would block on Win.
        w.close()
        r.close()

    def test_lock_out_of_context_pair(self):
        with raises(GIPCLocked):
            with pipe() as (r, w):
                # Fill up pipe and try to write more than pipe can hold
                # (makes `put` block when there is no reader).
                # Buffer is quite large on Windows.
                gw = gevent.spawn(lambda w: w.put(LONGERTHANBUFFER), w)
                gevent.sleep(SHORTTIME)
                # Context manager tries to close writer first, fails,
                # and must close reader nevertheless.
        # Kill greenlet (free lock on writer) and close writer.
        gw.kill(block=False)
        gevent.sleep(-1)
        w.close()

    def test_lock_out_of_context_pair_2(self):
        with raises(GIPCLocked):
            with pipe() as (r, w):
                gr = gevent.spawn(lambda r: r.get(), r)
                gevent.sleep(SHORTTIME)
                # Context manager tries to close writer first, succeeds,
                # and fails during closing reader.
        gr.kill(block=False)
        gevent.sleep(-1)
        r.close()


@mark.skipif('WINDOWS')
class TestGetTimeout(object):
    """Test timeout feature of `_GIPCReader` on POSIX-compliant systems.
    """
    def teardown(self):
        check_for_handles_left_open()

    def test_simpletimeout_expires(self):
        with pipe() as (r, w):
            t = gevent.Timeout.start_new(SHORTTIME)
            try:
                r.get(timeout=t)
                assert False
            except gevent.Timeout as raised_timeout:
                if t is not raised_timeout:
                    raise

    def test_simpletimeout_expires_contextmanager(self):
        with pipe() as (r, w):
            with gevent.Timeout(SHORTTIME, False) as t:
                r.get(timeout=t)
                assert False

    def test_simpletimeout_doesnt_expire(self):
        with pipe() as (r, w):
            with gevent.Timeout(SHORTTIME, False) as t:
                w.put('')
                r.get(timeout=t)
                return
        assert False


class TestDuplexHandleBasic(object):
    """Test duplex handle behavior in single process.
    """
    def teardown(self):
        check_for_handles_left_open()

    def test_simple(self):
        h1, h2 = pipe(duplex=True)
        assert len(get_all_handles()) == 4
        h1.put(1)
        h2.put(2)
        assert h2.get() == 1
        assert h1.get() == 2
        h1.close()
        h2.close()

    def test_context_simple(self):
        with pipe(duplex=True) as (h1, h2):
            h1.put(1)
            assert h2.get() == 1
            h2.put(2)
            assert h1.get() == 2

    def test_context_close(self):
        with pipe(duplex=True) as (h1, h2):
            fd1 = h1._reader._fd
            fd2 = h1._writer._fd
            fd3 = h2._reader._fd
            fd4 = h2._writer._fd

        # Make sure the C file descriptors are closed.
        for f in (fd1, fd2, fd3, fd4):
            with raises(OSError):
                os.close(f)

    def test_context_single_close(self):
        h1, h2 = pipe(duplex=True)
        with h1 as side1:
            fd1 = side1._reader._fd
            fd2 = side1._writer._fd
        # Make sure the C file descriptors are closed.
        with raises(OSError):
            os.close(fd1)
        with raises(OSError):
            os.close(fd2)
        with raises(GIPCClosed):
            h1.close()
        h2.close()

    def test_close_in_context(self):
        with pipe(duplex=True) as (h1, h2):
            h1.put('')
            h2.get()
            h1.close()
            h2.close()

    def test_lock_out_of_context_single(self):
        h1, h2 = pipe(True)
        g = gevent.spawn(lambda h: h.get(), h1)
        gevent.sleep(SHORTTIME)
        with raises(GIPCLocked):
            with h1:
                pass
                # Can't close h1 reader on exit, as it is locked in `g`.
        g.kill(block=False)
        # Ensure killing via 'context switch', i.e. yield control to other
        # coroutines (otherwise the subsequent close attempt may fail with
        # `GIPCLocked` error).
        gevent.sleep(-1)
        h2.close()  # Closes read and write handles of h2.
        assert h1._writer._closed
        assert not h1._reader._closed
        h1.close()  # Closes read handle, ignore that writer is already closed.
        assert h1._reader._closed

    def test_lock_out_of_context_pair(self):
        with raises(GIPCLocked):
            with pipe(True) as (h1, h2):
                # Write more to pipe than pipe buffer can hold
                # (makes `put` block when there is no reader).
                # Buffer is quite large on Windows.
                gw = gevent.spawn(lambda h: h.put(LONGERTHANBUFFER), h1)
                gevent.sleep(SHORTTIME)
                # Context manager tries to close h2 reader, h2 writer, and
                # h1 writer first. Fails upon latter, must still close
                # h1 reader after that.
        assert not h1._writer._closed
        assert h1._reader._closed
        assert h2._writer._closed
        assert h2._reader._closed
        # Kill greenlet (free lock on h1 writer), close h1 writer.
        gw.kill(block=False)
        gevent.sleep(-1)
        h1.close()
        assert h1._writer._closed

    def test_lock_out_of_context_pair_2(self):
        with raises(GIPCLocked):
            with pipe(True) as (h1, h2):
                gr = gevent.spawn(lambda h: h.get(), h2)
                gevent.sleep(SHORTTIME)
                # Context succeeds closing h1 reader and writer. Fails during
                # closing h2 reader.
        assert not h2._reader._closed
        assert h1._reader._closed
        assert h2._writer._closed
        assert h1._writer._closed
        gr.kill(block=False)
        gevent.sleep(-1)
        h2.close()

    def test_lock_out_of_context_pair_3(self):
        with raises(GIPCLocked):
            with pipe(True) as (h1, h2):
                gr1 = gevent.spawn(lambda h: h.get(), h1)
                gr2 = gevent.spawn(lambda h: h.get(), h2)
                gevent.sleep(SHORTTIME)
                # Context succeeds closing h2 writer, fails upon closing h2
                # reader. Proceeds closing h1 writer, succeeds, closes h1
                # reader and fails.
        assert not h2._reader._closed
        assert not h1._reader._closed
        assert h2._writer._closed
        assert h1._writer._closed
        gr1.kill(block=False)
        gr2.kill(block=False)
        gevent.sleep(-1)
        h2.close()
        h1.close()

    def test_lock_out_of_context_pair_4(self):
        with raises(GIPCLocked):
            with pipe(True) as (h1, h2):
                # Write more to pipe than pipe buffer can hold
                # (makes `put` block when there is no reader).
                # Buffer is quite large on Windows.
                gw1 = gevent.spawn(lambda h: h.put(LONGERTHANBUFFER), h1)
                gw2 = gevent.spawn(lambda h: h.put(LONGERTHANBUFFER), h2)
                gevent.sleep(SHORTTIME)
                # Context fails closing h2 writer, succeeds upon closing h2
                # reader. Proceeds closing h1 writer, fails, closes h1
                # reader and succeeds.
        assert h2._reader._closed
        assert h1._reader._closed
        assert not h2._writer._closed
        assert not h1._writer._closed
        gw1.kill(block=False)
        gw2.kill(block=False)
        gevent.sleep(-1)
        h2.close()
        h1.close()

    def test_double_close(self):
        with pipe(True) as (h1, h2):
            pass
        with raises(GIPCClosed):
            h2.close()
        with raises(GIPCClosed):
            h1.close()


class TestDuplexHandleIPC(object):
    """Test duplex handles for inter-process communication.
    """
    def teardown(self):
        check_for_handles_left_open()

    def test_simple_echo(self):
        with pipe(True) as (hchild, hparent):
            p = start_process(duplchild_simple_echo, (hchild, ))
            hparent.put("MSG")
            assert hparent.get() == "MSG"
            p.join()

    def test_time_sync(self):
        with pipe(duplex=True) as (cend, pend):
            p = start_process(duplchild_time_sync, args=(cend, ))
            pend.put("SYN")
            assert pend.get() == "ACK"
            ptime = time.time()
            ctime = pend.get()
            # Require small time delta. Note: on Windows on a machine with
            # diverse load I have seen this time difference to be 0.02 seconds.
            # See https://github.com/jgehrcke/gipc/issues/70.
            assert abs(ptime - ctime) < 0.03
            p.join()

    def test_circular_forward(self):
        with pipe(True) as (p11, p12):
            with pipe(True) as (p21, p22):
                with pipe(True) as (p31, p32):
                    # Spawn two forwarders.
                    forwarder1 = start_process(
                        duplchild_circular_forward, (p12, p21))
                    forwarder2 = start_process(
                        duplchild_circular_forward, (p22, p31))
                    # Make sure that only 2 of 6 handles are usable.
                    for h in (p12, p21, p22, p31):
                        with raises(GIPCClosed):
                            h.put(0)
                    # Send messages on their journey through children.
                    for _ in range(100):
                        p11.put("BABUUUZ")
                        assert p32.get() == "BABUUUZ"
                    p11.put("stop")
                    forwarder1.join()
                    forwarder2.join()


def duplchild_circular_forward(receiver, sender):
    with receiver:
        with sender:
            msg = None
            while msg != "stop":
                msg = receiver.get()
                sender.put(msg)


def duplchild_time_sync(cend):
    with cend:
        assert cend.get() == "SYN"
        cend.put("ACK")
        cend.put(time.time())


def duplchild_simple_echo(h):
    h.put(h.get())


class TestPipeCodecs(object):
    """Test pipe encoding/decoding API. The default behavior
    is tested thoroughly in all other tests involving pipe().
    """
    @staticmethod
    def readlet(r):
        return r.get()

    @staticmethod
    def writelet(w, data):
        w.put(data)

    def teardown(self):
        check_for_handles_left_open()

    def test_default(self):
        data = [10]
        with pipe(encoder='default', decoder='default') as (r, w):
            gw = gevent.spawn(self.writelet, w, data)
            gr = gevent.spawn(self.readlet, r)
            assert data == gr.get()
            gw.join()

    def test_callable_raw(self):
        data = os.urandom(10000)
        with pipe(encoder=lambda x: x, decoder=lambda x: x) as (r, w):
            gw = gevent.spawn(self.writelet, w, data)
            gr = gevent.spawn(self.readlet, r)
            assert data == gr.get()
            gw.join()

    def test_raw(self):
        data = os.urandom(10000)
        with pipe(encoder=None, decoder=None) as (r, w):
            gw = gevent.spawn(self.writelet, w, data)
            gr = gevent.spawn(self.readlet, r)
            assert data == gr.get()
            gw.join()

    def test_json(self):
        import json
        data = {"a": 100}
        enc = lambda o: json.dumps(o).encode("ascii")
        dec = lambda b: json.loads(b.decode("ascii"))
        with pipe(encoder=enc, decoder=dec) as (r, w):
            gw = gevent.spawn(self.writelet, w, data)
            gr = gevent.spawn(self.readlet, r)
            assert data == gr.get()
            gw.join()

    def test_zlib(self):
        import zlib
        data = os.urandom(10000)
        with pipe(encoder=zlib.compress, decoder=zlib.decompress) as (r, w):
            gw = gevent.spawn(self.writelet, w, data)
            gr = gevent.spawn(self.readlet, r)
            assert data == gr.get()
            gw.join()

    def test_not_callable_encoder(self):
        data = os.urandom(10000)
        with raises(GIPCError):
            with pipe(encoder=1, decoder=lambda x: x) as (r, w):
                pass

    def test_not_callable_decoder(self):
        data = os.urandom(10000)
        with raises(GIPCError):
            with pipe(encoder=lambda x: x, decoder=1) as (r, w):
                pass

    def test_raw_pipe_across_processes(self):
        data = b'abc'

        with pipe(encoder=None, decoder=None) as (r, w):
            start_process(child_test_raw_pipe_across_processes, (r, ))


def child_test_raw_pipe_across_processes(r):
    assert r.get() == b'abc'


class TestSimpleUseCases(object):
    """Test very basic usage scenarios of gipc (pure gipc+gevent).
    """
    def teardown(self):
        check_for_handles_left_open()

    @mark.skipif('WINDOWS')
    def test_whatever_1(self):
        """
        From a writing child, fire into the pipe. In a greenlet in the parent,
        receive one of these messages and return it to the main greenlet.
        Expect message retrieval (child process creation) within a certain
        timeout interval. Terminate the child process after retrieval.
        """
        with pipe() as (r, w):
            def readgreenlet(reader):
                with gevent.Timeout(SHORTTIME * 5, False) as t:
                    m = reader.get(timeout=t)
                    return m
            p = start_process(usecase_child_a, args=(w, ))
            # Wait for process to send first message:
            r.get()
            # Second message must be available immediately now.
            g = gevent.spawn(readgreenlet, r)
            m = r.get()
            assert g.get() == "SPLASH"
            p.terminate()
            p.join()
            assert p.exitcode == -signal.SIGTERM

    @mark.skipif('WINDOWS')
    def test_whatever_2(self):
        """
        Time-synchronize two child processes via two unidirectional channels.
        Uses timeout control in children.
        """
        # First pipe for sync.
        with pipe() as (syncreader, syncwriter):
            # Second pipe for communication.
            with pipe() as (r, w):
                # Send messages
                pw = start_process(usecase_child_b, args=(w, syncreader))
                # Receive messages
                pr = start_process(usecase_child_c, args=(r, syncwriter))
                pw.join()
                pr.join()
                assert pw.exitcode == 0
                assert pr.exitcode == 5

    def test_whatever_3(self):
        """
        Circular messaging. Random messages are stored in `sendlist` in parent.
        sendlist -> sendqueue(greenlet, parent)
        sendqueue -> forthpipe to child (greenlet, parent)
        forthpipe -> recvqueue (greenlet, child)
        recvqueue -> backpipe to parent (greenlet, child)
        backpipe -> recvlist (greenlet, parent)
        assert sendlist == recvlist
        """
        sendlist = [random.choice('UFTATA') for x in range(100)]
        sendlist.append("STOP")
        sendqueue = gevent.queue.Queue()
        def g_from_list_to_sendq():
            for item in sendlist:
                sendqueue.put(item)

        def g_from_q_to_forthpipe(forthwriter):
            while True:
                m = sendqueue.get()
                forthwriter.put(m)
                if m == "STOP":
                    break

        def g_from_backpipe_to_recvlist(backreader):
            recvlist = []
            while True:
                m = backreader.get()
                recvlist.append(m)
                if m == "STOP":
                    break
            return recvlist

        with pipe() as (forthr, forthw):
            with pipe() as (backr, backw):
                p = start_process(usecase_child_d, args=(forthr, backw))
                g1 = gevent.spawn(g_from_list_to_sendq)
                g2 = gevent.spawn(g_from_q_to_forthpipe, forthw)
                g3 = gevent.spawn(g_from_backpipe_to_recvlist, backr)
                g1.get()
                g2.get()
                p.join()
                recvlist = g3.get()
                assert recvlist == sendlist


def usecase_child_d(forthreader, backwriter):
    recvqueue = gevent.queue.Queue()
    def g_from_forthpipe_to_q(forthreader):
        while True:
            m = forthreader.get()
            recvqueue.put(m)
            if m == "STOP":
                break

    def g_from_q_to_backpipe(backwriter):
        while True:
            m = recvqueue.get()
            backwriter.put(m)
            if m == "STOP":
                break

    g1 = gevent.spawn(g_from_forthpipe_to_q, forthreader)
    g2 = gevent.spawn(g_from_q_to_backpipe, backwriter)
    g1.get()
    g2.get()


def usecase_child_a(writer):
    with writer:
        while True:
            writer.put("SPLASH")
            gevent.sleep(ALMOSTZERO)


def usecase_child_b(writer, syncreader):
    with syncreader:
        # Wait for partner process to start up.
        assert syncreader.get() == 'SYN'
        writer.put('SYNACK')
    with writer:
        writer.put("CHICKEN")


def usecase_child_c(reader, syncwriter):
    with syncwriter:
        # Tell partner process that we are up and running!
        syncwriter.put("SYN")
        # Wait for confirmation.
        assert reader.get() == 'SYNACK'
    with reader:
        # Processes are synchronized. CHICKEN must be incoming within no time.
        with gevent.Timeout(SHORTTIME, False) as t:
            assert reader.get(timeout=t) == "CHICKEN"
        # Timeout is invalidated.
        # The write end becomes closed right now.
        with raises(EOFError):
            reader.get()
    sys.exit(5)


class TestComplexUseCases(object):
    """Tests with increased complexity, also involving server components of
    gevent. Reproduction of common usage scenarios.
    """
    def teardown(self):
        check_for_handles_left_open()

    def test_getaddrinfo_mp(self):
        """This test would make gevent's hub threadpool kill upon hub
        destruction in child block forever. Gipc resolves this by killing
        threadpool even harder.
        """
        import gevent.socket as socket
        socket.getaddrinfo("localhost", 21)
        p = start_process(target=complchild_test_getaddrinfo_mp)
        p.join(timeout=1)
        assert p.exitcode == 0

    def test_threadpool_resolver_mp(self):
        h = gevent.get_hub()
        t = h.threadpool
        r = h.resolver
        p = start_process(target=complchild_test_threadpool_resolver_mp)
        # Note(JP): seen this fail once on Windows CI with a timeout of 1 s.
        p.join(timeout=2)
        assert p.exitcode == 0

    def test_wsgi_scenario(self):
        from gevent.pywsgi import WSGIServer

        def serve(http_server):
            http_server.serve_forever()

        def hello_world(environ, start_response):
            # Generate response in child process.
            with pipe() as (reader, writer):
                start_response('200 OK', [('Content-Type', 'text/html')])
                rg = start_process(
                    target=complchild_test_wsgi_scenario_respgen,
                    args=(writer, ))
                response = reader.get()
                rg.join()
                assert rg.exitcode == 0
            return [response]

        # Call `urlopen` with `None` in the parent before forking. This works
        # around a special type of segfault in the child after fork on MacOS.
        # Doh! See https://bugs.python.org/issue27126 and
        # https://github.com/jgehrcke/gipc/issues/52
        try:
            import urllib.request as request
        except ImportError:
            import urllib2 as request
        try:
            result = request.urlopen(None)
        except AttributeError:
            pass

        http_server = WSGIServer(('localhost', 0), hello_world)
        servelet = gevent.spawn(serve, http_server)
        # Wait for server being bound to socket.
        while True:
            if http_server.address[1] != 0:
                break
            gevent.sleep(0.05)
        client = start_process(
            target=complchild_test_wsgi_scenario_client,
            args=(http_server.address, ))
        client.join()
        assert client.exitcode == 0
        servelet.kill()
        servelet.get()  # get() is join and re-raises Exception.

    def test_multi_duplex(self):
        def duplex():
            with pipe() as (r, w):
                with pipe() as (r2, w2):
                    p = start_process(complchild_test_multi_duplex, (r, w2))
                    w.put("msg")
                    assert r2.get() == "msg"
                    p.join()
                    assert p.exitcode == 0

        duplexlets = [gevent.spawn(duplex) for _ in range(10)]
        for g in duplexlets:
            g.get()


def complchild_test_multi_duplex(r, w):
    w.put(r.get())


def complchild_test_wsgi_scenario_respgen(writer):
    writer.put(b"response")


def complchild_test_wsgi_scenario_client(http_server_address):
    # On MacOS doing the usage of `urlopen` might crash right after fork because
    # it reads proxy settings from the OS via some special system calls. We
    # (hope that we can) prevent this crash by calling `urlopen` already in the
    # parent. See https://github.com/jgehrcke/gipc/issues/52
    try:
        # Python 3
        import urllib.request as request
    except ImportError:
        # Python 2
        import urllib2 as request
    result = request.urlopen("http://%s:%s/" % http_server_address)
    assert result.read() == b"response"


def complchild_test_threadpool_resolver_mp():
    h = gevent.get_hub()
    t = h.threadpool
    r = h.resolver


def complchild_test_getaddrinfo_mp():
    return


class TestSignals(object):
    """Tests involving signal handling.
    """

    def teardown(self):
        check_for_handles_left_open()
        # One could verify that signal handlers are not left improperly
        # by a test case, but libev's signal handling might go through
        # signalfd() which we cannot detect here anyway. So the test cases
        # have to properly clean up their signal handling modifications
        # themselves.

    def test_orphaned_signal_watcher(self):
        # Install libev-based signal watcher.
        s = gevent.signal(signal.SIGTERM, signals_test_sigterm_handler)
        # Normal behavior: signal handlers become inherited by children.
        # Bogus behavior of libev-based signal watchers in child process:
        # They should not be active anymore when 'orphaned' (when their
        # corresponding event loop has been destroyed). What happens, however:
        # The old handler stays active and registering a new handler does not
        # 'overwrite' the old one -- both are active.
        # Since this test is about testing the behavior of 'orphaned' libev
        # signal watchers, the signal must be transmitted *after* event loop
        # recreation, so wait here for the child process to go through
        # the hub & event loop destruction (and recreation) process before
        # sending the signal. Waiting is realized with sync through pipe.
        # Without cleanup code in gipc, the inherited but orphaned libev signal
        # watcher would be active in the fresh event loop and trigger the
        # handler. This is a problem. With cleanup code, this handler must
        # never be called. Child exitcode 20 means that the inherited handler
        # has been called, -15 (-signal.SIGTERM) means that the child was
        # actually killed by SIGTERM within a certain short time interval.
        # Returncode 0 would mean that the child finished normally after that
        # short time interval.
        with pipe() as (r, w):
            p = start_process(signals_test_child_a, (w,))
            assert r.get() == p.pid
            os.kill(p.pid, signal.SIGTERM)
            p.join()
            if not WINDOWS:
                assert p.exitcode == -signal.SIGTERM
            else:
                assert p.exitcode == signal.SIGTERM
        s.cancel()

    @mark.skipif('WINDOWS')
    def test_signal_handlers_default(self):
        p = start_process(signals_test_child_defaulthandlers)
        p.join()
        # Child exits normally when all signal dispositions are default.
        assert p.exitcode == 0


def signals_test_child_defaulthandlers():
    for s in signals_to_reset:
        assert signal.getsignal(s) is signal.SIG_DFL


def signals_test_sigterm_handler():
    sys.exit(20)


def signals_test_child_a(w):
    w.put(os.getpid())
    gevent.sleep(SHORTTIME)
    sys.exit(0)


if __name__ == "__main__":
    pass
