# -*- coding: utf-8 -*-
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
from gipc import (start_process, pipe, GIPCError, GIPCClosed, GIPCLocked,
                  get_all_handles, set_all_handles)

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

class TestComm():
    """
    Flow for each test_method:
    o = TestClass()
    o.setup()
    try:
        o.test_method()
    finally:
        o.teardown()
    """
    def setup(self):
        self.rh, self.wh = pipe()
        self._greenlets_to_be_killed = []

    def teardown(self):
        # Make sure to not leak file descriptors.
        if get_all_handles():
            for h in get_all_handles():
                try:
                    h.close()
                    os.close(h._fd)
                except (OSError, GIPCError, TypeError):
                    pass
            set_all_handles([])
        for g in self._greenlets_to_be_killed:
            g.kill()

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

    def test_twoclose(self):
        self.wh.close()
        with raises(GIPCClosed):
            self.wh.close()

    def test_closewrite(self):
        self.wh.close()
        with raises(GIPCClosed):
            self.wh.put('')

    def test_closeread(self):
        self.rh.close()
        with raises(GIPCClosed):
            self.rh.get()

    def test_readclose(self):
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self._greenlets_to_be_killed.append(g)
        gevent.sleep(SHORTTIME)
        with raises(GIPCLocked):
            self.rh.close()

    def test_closewrite_read(self):
        self.wh.close()
        with raises(EOFError):
            self.rh.get()

    def test_closeread_write(self):
        self.rh.close()
        with raises(OSError):
            self.wh.put('')


class TestProcess():
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
    def setup(self):
        self.rh, self.wh = pipe()
        self.rh2, self.wh2 = pipe()
        self._greenlets_to_be_killed = []

    def teardown(self):
        # Make sure to not leak file descriptors.
        if get_all_handles():
            for h in get_all_handles():
                try:
                    h.close()
                    os.close(h._fd)
                except (OSError, GIPCError, TypeError):
                    pass
            set_all_handles([])
        for g in self._greenlets_to_be_killed:
            g.kill()

    def test_singlemsg_long_list(self):
        m = [1] * LONG
        p = start_process(ipc_readchild, args=(self.rh, m))
        self.wh.put(m)
        p.join()
        assert p.exitcode == 0

    def test_twochannels_singlemsg(self):
        m1 = "OK"
        m2 = "FOO"
        p = start_process(ipc_child_b, args=(self.rh, self.rh2, m1, m2))
        self.wh.put(m1)
        self.wh2.put(m2)
        p.join()
        assert p.exitcode == 0

    def test_childparentcomm_withinchildcomm(self):
        m1 = "OK"
        m2 = "FOO"
        p = start_process(
            target=ipc_child_c, args=(self.rh, self.rh2, m1, m2))
        self.wh.put(m1)
        self.wh2.put(m2)
        p.join()
        assert p.exitcode == 0

    def test_childchildcomm(self):
        m = {("KLADUSCH",): "foo"}
        pr = start_process(ipc_readchild, args=(self.rh, m))
        pw = start_process(ipc_writechild, args=(self.wh, m))
        pr.join()
        pw.join()
        assert pr.exitcode == 0
        assert pw.exitcode == 0

    def test_handler_after_transfer_to_child(self):
        p = start_process(ipc_child_boring_reader, args=(self.rh,))
        with raises(GIPCError):
            self.rh.close()
        p.join()
        assert p.exitcode == 0

    def test_handler_in_nonregistered_process(self):
        p = multiprocessing.Process(target=ipc_child_d, args=(self.rh, ))
        p.start()
        p.join()
        assert p.exitcode == 0
        self.rh.close()

    def test_child_in_child_in_child_comm(self):
        m = "RATZEPENG"
        p = start_process(ipc_child_f, args=(self.wh, m))
        p.join()
        assert m == self.rh.get()
        assert p.exitcode == 0


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
    gr.join()
    gw.join()
    local_reader.close()
    local_writer.close()
    # Receive second message from parent.
    assert r2.get() == m2


def ipc_child_d(r):
    with raises(GIPCError):
        r.close()


def ipc_child_f(w, m):
    i = start_process(ipc_child_f2, args=(w, m))
    i.join()


def ipc_child_f2(w, m):
    ii = start_process(ipc_child_f3, args=(w, m))
    ii.join()


def ipc_child_f3(w, m):
    w.put(m)
    w.close()


class TestContextManager():
    def teardown(self):
        if get_all_handles():
            for h in get_all_handles():
                try:
                    h.close()
                    os.close(h._fd)
                except (OSError, GIPCError, TypeError):
                    pass
            set_all_handles([])
            raise Exception("Cleanup was not successful.")

    def test_all_handles_length(self):
        r, w = pipe()
        assert len(get_all_handles()) == 2
        r.close()
        w.close()

    def test_combi(self):
        with pipe() as (r, w):
            fd1 = r._fd
            fd2 = w._fd
        # Make sure the C file descriptors are closed.
        with raises(OSError):
            os.close(fd1)
        with raises(OSError):
            os.close(fd2)
        # Make sure the module's self-cleanup works properly.
        assert not len(get_all_handles())

    def test_single_reader(self):
        r, w = pipe()
        with w as foo:
            fd = foo._fd
        # Make sure the C file descriptor is closed.
        with raises(OSError):
            os.close(fd)
        assert len(get_all_handles()) == 1
        with raises(GIPCClosed):
            w.close()
        r.close()
        assert not len(get_all_handles())

    def test_single_writer(self):
        r, w = pipe()
        with r as foo:
            fd = foo._fd
        # Make sure the C file descriptor is closed.
        with raises(OSError):
            os.close(fd)
        assert len(get_all_handles()) == 1
        with raises(GIPCClosed):
            r.close()
        w.close()
        assert not len(get_all_handles())

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
                gw = gevent.spawn(lambda w: w.put("A" * 9999999), w)
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
    def teardown(self):
        if get_all_handles():
            for h in get_all_handles():
                try:
                    h.close()
                    os.close(h._fd)
                except (OSError, GIPCError, TypeError):
                    pass
            set_all_handles([])
            raise Exception("Cleanup was not successful.")

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


class TestSimpleUseCases():
    """Tests reproducing basic usage scenarios of gipc.
    """
    def teardown(self):
        if get_all_handles():
            for h in get_all_handles():
                try:
                    h.close()
                    os.close(h._fd)
                except (OSError, GIPCError, TypeError):
                    pass
            set_all_handles([])
            raise Exception("Cleanup was not successful.")

    @mark.skipif('WINDOWS')
    def test_whatever_1(self):
        """
        From a writing child, fire into the pipe. In a greenlet in the parent,
        receive one of these messages and return it to the main greenlet.
        Terminate the child process.
        Looks like a timeout of 0.01 s does not reliably lead to success.
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
        Time-synchronize two child processes.
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
        Circular messaging! Random messages are in `sendlist` in parent.
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
                g1.join()
                g2.join()
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
    g1.join()
    g2.join()


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
    """Tests with increased complexity; involving other parts of gevent
    and reproducing common usage scenarios.
    """
    def teardown(self):
            if get_all_handles():
                for h in get_all_handles():
                    try:
                        h.close()
                        os.close(h._fd)
                    except (OSError, GIPCError, TypeError):
                        pass
                set_all_handles([])
                raise Exception("Cleanup was not successful.")

    def test_getaddrinfo_mp(self):
        """This test would make gevent's hub threadpool kill upon hub
        destruction in child block forever. Gipc resolves this by killing
        threadpool even harder.
        """
        import gevent.socket as socket
        socket.getaddrinfo("localhost", 21)
        p = start_process(target=child_test_getaddrinfo_mp)
        p.join(timeout=1)
        assert p.exitcode == 0

    def test_threadpool_resolver_mp(self):
        h = gevent.get_hub()
        t = h.threadpool
        r = h.resolver
        p = start_process(target=child_test_threadpool_resolver_mp)
        p.join(timeout=1)
        assert p.exitcode == 0


def child_test_threadpool_resolver_mp():
    h = gevent.get_hub()
    t = h.threadpool
    r = h.resolver


def child_test_getaddrinfo_mp():
    return


if __name__ == "__main__":
    pass
