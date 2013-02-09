﻿# -*- coding: utf-8 -*-
#
#   Copyright (C) 2012 - 2013 Jan-Philip Gehrcke
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import sys
import os
import time
import signal
import multiprocessing
import random

import gevent
import gevent.queue
sys.path.insert(0, os.path.abspath('..'))
from gipc import start_process, pipe, GIPCError, GIPCClosed, GIPCLocked
from gipc.gipc import _get_all_handles as get_all_handles
from gipc.gipc import _set_all_handles as set_all_handles

WINDOWS = sys.platform == "win32"

# py.test runs tests by order of definition. This is useful for running simple,
# fundamental tests first and more complex tests later.
from py.test import raises, mark
# Nose is great and all, but can run tests in alphabetical order only.
# from nose.tools import raises

import logging
logging.basicConfig(
  format='%(asctime)s,%(msecs)-6.1f [%(process)-5d]%(funcName)s# %(message)s',
  datefmt='%H:%M:%S')
log = logging.getLogger()
log.setLevel(logging.DEBUG)

LONG = 999999
SHORTTIME = 0.01
ALMOSTZERO = 0.00001
LONGERTHANBUFFER = "A" * 9999999


def check_for_handles_left_open():
    """Frequently used teardown test method.

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


class TestComm():
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
            return [reader.get() for _ in xrange(2)]
        gw1 = gevent.spawn(gwrite, self.wh, m)
        gw2 = gevent.spawn(gwrite, self.wh, m)
        gr = gevent.spawn(gread, self.rh)
        assert [m, m] == gr.get()
        gw1.get()
        gw2.get()

    def test_all_handles_length(self):
        assert len(get_all_handles()) == 2


class TestClose():
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


class TestProcess():
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
        p.terminate()
        p.join()
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
        assert p.exitcode is None
        gevent.sleep(3*SHORTTIME)
        assert p.exitcode == 0
        p.join()


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


class TestIPC():
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
            assert p.exitcode == None
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


class TestContextManager():
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
class TestGetTimeout():
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
            except gevent.Timeout, raised_timeout:
                if not t is raised_timeout:
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


class TestDuplexHandleBasic():
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
        h2.close() # Closes read and write handles of h2.
        assert h1._writer._closed
        assert not h1._reader._closed
        h1.close() # Closes read handle, ignore that writer is already closed.
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


class TestDuplexHandleIPC():
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


def duplchild_simple_echo(h):
    h.put(h.get())


class TestSimpleUseCases():
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
                with gevent.Timeout(SHORTTIME*5, False) as t:
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
        sendlist = [random.choice('UFTATA') for x in xrange(100)]
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


class TestComplexUseCases():
    """Tests with increased complexity; involving server components of gevent.
    Rproduction of common usage scenarios.
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
        p.join(timeout=1)
        assert p.exitcode == 0

    def test_wsgi_scenario(self):
        from gevent.wsgi import WSGIServer

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
            yield response

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
        servelet.kill()
        servelet.get() # get() is join and re-raises Exception.

    def test_multi_duplex(self):
        def duplex():
            with pipe() as (r, w):
                with pipe() as (r2, w2):
                    p = start_process(complchild_test_multi_duplex, (r, w2))
                    w.put("msg")
                    assert r2.get() == "msg"
                    p.join()

        duplexlets = [gevent.spawn(duplex) for _ in xrange(10)]
        for g in duplexlets:
            g.get()


def complchild_test_multi_duplex(r, w):
    w.put(r.get())


def complchild_test_wsgi_scenario_respgen(writer):
    writer.put("response")


def complchild_test_wsgi_scenario_client(http_server_address):
    import urllib2
    result = urllib2.urlopen("http://%s:%s/" % http_server_address)
    assert result.read() == "response"


def complchild_test_threadpool_resolver_mp():
    h = gevent.get_hub()
    t = h.threadpool
    r = h.resolver


def complchild_test_getaddrinfo_mp():
    return


if __name__ == "__main__":
    pass
