﻿# -*- coding: utf-8 -*-
#
#   Copyright (C) 2012 Jan-Philip Gehrcke
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
import gevent

sys.path.insert(0, os.path.abspath('..'))
from gpipe import Pipe, GPipeError, GPipeClosed, GPipeLocked
import gpipe


# py.test runs tests by order of definition. Useful for running simple,
# fundamental tests first and more complex tests later.
from py.test import raises
# Nose is great and all, but runs tests alphabetically. Can't be changed.
# from nose.tools import raises

#import logging
#logging.basicConfig(
#    format='%(asctime)s,%(msecs)-6.1f [%(process)-5d]%(funcName)s# %(message)s',
#    datefmt='%H:%M:%S')
#log = logging.getLogger()
#log.setLevel(logging.DEBUG)

LONG = 999999
SHORTTIME = 0.01
ALMOSTZERO = 0.00001

class TestComm():
    """
    Flow for each test_method:
    o = TestPipe()
    o.setup()
    try:
        o.test_method()
    finally:
        o.teardown()
    """
    def setup(self):
        self.rh, self.wh = Pipe()
        self._greenlets_to_be_killed = []

    def teardown(self):
        # Make sure to not leak file descriptors
        try:
            self.rh.close()
            os.close(self.rh._fd)
        except:
            pass
        try:
            self.wh.close()
            os.close(self.wh._fd)
        except:
            pass
        gpipe._all_handles = []
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
        with raises(GPipeClosed):
            self.wh.close()

    def test_closewrite(self):
        self.wh.close()
        with raises(GPipeClosed):
            self.wh.put('')

    def test_closeread(self):
        self.rh.close()
        with raises(GPipeClosed):
            self.rh.get()

    def test_readclose(self):
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self._greenlets_to_be_killed.append(g)
        gevent.sleep(SHORTTIME)
        with raises(GPipeLocked):
            self.rh.close()

    def test_closewrite_read(self):
        self.wh.close()
        with raises(EOFError):
            self.rh.get()


class TestProcess():
    def test_is_alive_true(self):
        p = gpipe.start_process(p_child_a)
        assert p.is_alive()

    def test_is_alive_false(self):
        p = gpipe.start_process(p_child_a)
        p.join()
        assert not p.is_alive()

    def test_exitcode_0(self):
        p = gpipe.start_process(p_child_a)
        p.join()
        assert p.exitcode == 0

    def test_exitcode_sigkill(self):
        p = gpipe.start_process(p_child_b)
        p.join()
        assert p.exitcode == -signal.SIGKILL

    def test_exitcode_1(self):
        p = gpipe.start_process(p_child_c)
        p.join()
        assert p.exitcode == 1

    def test_pid(self):
        p = gpipe.start_process(p_child_a)
        p.join()
        assert p.pid is not None

    def test_terminate(self):
        p = gpipe.start_process(gevent.sleep, args=(1,))
        p.terminate()
        p.join()
        assert p.exitcode == -signal.SIGTERM

    def test_child_in_child_in_child(self):
        p = gpipe.start_process(p_child_e)
        p.join()

    def test_join_timeout(self):
        p = gpipe.start_process(gevent.sleep, args=(0.1, ))
        p.join(ALMOSTZERO)
        assert p.is_alive()
        p.join()

    def test_typecheck(self):
        with raises(TypeError):
            gpipe.start_process(gevent.sleep, args="peter")

    def test_typecheck(self):
        with raises(TypeError):
            gpipe.start_process(gevent.sleep, kwargs="peter")


def p_child_a():
    gevent.sleep(SHORTTIME)


def p_child_b():
    os.kill(os.getpid(), signal.SIGKILL)


def p_child_c():
    sys.exit(1)


def p_child_e():
    i = gpipe.start_process(p_child_e2)
    i.join()


def p_child_e2():
    ii = gpipe.start_process(cp_hild_e3)
    ii.join()


def p_child_e3():
    pass


class TestIPC():
    def setup(self):
        self.rh, self.wh = Pipe()
        self.rh2, self.wh2 = Pipe()
        self._greenlets_to_be_killed = []

    def teardown(self):
        # Make sure to not leak file descriptors
        try:
            self.rh.close()
            os.close(self.rh._fd)
        except:
            pass
        try:
            self.wh.close()
            os.close(self.wh._fd)
        except:
            pass
        try:
            self.rh2.close()
            os.close(self.rh2._fd)
        except:
            pass
        try:
            self.wh2.close()
            os.close(self.wh2._fd)
        except:
            pass
        gpipe._all_handles = []
        for g in self._greenlets_to_be_killed:
            g.kill()

    def test_singlemsg_long_list(self):
        m = [1] * LONG
        p = gpipe.start_process(ipc_readchild, args=(self.rh, m))
        self.wh.put(m)
        p.join()

    def test_twochannels_singlemsg(self):
        m1 = "OK"
        m2 = "FOO"
        p = gpipe.start_process(ipc_child_b, args=(self.rh, self.rh2, m1, m2))
        self.wh.put(m1)
        self.wh2.put(m2)
        p.join()

    def test_childparentcomm_withinchildcomm(self):
        m1 = "OK"
        m2 = "FOO"
        p = gpipe.start_process(
            target=ipc_child_c, args=(self.rh, self.rh2, m1, m2))
        self.wh.put(m1)
        self.wh2.put(m2)
        p.join()

    def test_childchildcomm(self):
        m = {("KLADUSCH",): "foo"}
        pr = gpipe.start_process(ipc_readchild, args=(self.rh, m))
        pw = gpipe.start_process(ipc_writechild, args=(self.wh, m))
        pr.join()
        pw.join()

    def test_handler_after_transfer_to_child(self):
        p = gpipe.start_process(ipc_child_boring_reader, args=(self.rh,))
        with raises(GPipeError):
            self.rh.close()
        p.join()

    def test_handler_in_nonregistered_process(self):
        p = multiprocessing.Process(target=ipc_child_d, args=(self.rh, ))
        p.start()
        p.join()
        self.rh.close()

    def test_child_in_child_in_child_comm(self):
        m = "RATZEPENG"
        p = gpipe.start_process(ipc_child_f, args=(self.wh, m))
        p.join()
        assert m == self.rh.get()


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
    local_reader, local_writer = Pipe()
    testmsg = [1] * LONG
    gw = gevent.spawn(lambda w: w.put(testmsg), local_writer)
    gr = gevent.spawn(lambda r: r.get(), local_reader)
    assert testmsg == gr.get()
    gr.join()
    gw.join()
    local_reader.close()
    local_writer.close()
    # Receive second message from parent
    assert r2.get() == m2


def ipc_child_d(r):
    try:
        r.close()
    except GPipeClosed:
        return
    assert False


def ipc_child_f(w, m):
    i = gpipe.start_process(ipc_child_f2, args=(w, m))
    i.join()


def ipc_child_f2(w, m):
    ii = gpipe.start_process(ipc_child_f3, args=(w, m))
    ii.join()


def ipc_child_f3(w, m):
    w.put(m)
    w.close()


class TestContextManager():
    def teardown(self):
        if gpipe._all_handles:
            raise Exception("Cleanup was not successful.")

    def test_both(self):
        with Pipe() as (r, w):
            w.put('')
            r.get()
        assert not len(gpipe._all_handles)
        r, w = Pipe()
        assert len(gpipe._all_handles) == 2
        r.close()
        w.close()

    def test_single_reader(self):
        r, w = Pipe()
        with w as foo:
            foo.put('')
        assert len(gpipe._all_handles) == 1
        with raises(GPipeClosed):
            w.close()
        r.close()
        assert not len(gpipe._all_handles)

    def test_single_writer(self):
        r, w = Pipe()
        with r as foo:
            pass
        assert len(gpipe._all_handles) == 1
        with raises(GPipeClosed):
            r.close()
        w.close()
        assert not len(gpipe._all_handles)


if __name__ == "__main__":
    pass
