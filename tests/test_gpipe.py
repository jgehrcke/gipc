# -*- coding: utf-8 -*-
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
import gevent

sys.path.insert(0, os.path.abspath('..'))
from gpipe import pipe, GPipeError
import gpipe
import multiprocessing
from nose.tools import *


class TestSingleProcess():
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
        self.rh, self.wh = pipe()
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
        m = "OK" * 999999
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self.wh.put(m)
        t = g.get()
        assert m == t

    def test_singlemsg_long_list(self):
        m = [1] * 999999
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self.wh.put(m)
        t = g.get()
        assert m == t

    def test_singlemsg_between_greenlets(self):
        m = [1] * 999999
        def gwrite(writer, m):
            writer.put(m)
        def gread(reader):
            return reader.get()
        gw = gevent.spawn(gwrite, self.wh, m)
        gr = gevent.spawn(gread, self.rh)
        t = gr.get()
        assert m == t

    def test_onewriter_two_readers(self):
        m = [1] * 999999
        def gwrite(writer, m):
            writer.put(m)
            writer.put(m)
        def gread(reader):
            return reader.get()
        gw = gevent.spawn(gwrite, self.wh, m)
        gr1 = gevent.spawn(gread, self.rh)
        gr2 = gevent.spawn(gread, self.rh)
        t1 = gr1.get()
        t2 = gr2.get()
        assert m == t1 == t2

    def test_twowriters_one_reader(self):
        m = [1] * 999999
        def gwrite(writer, m):
            writer.put(m)
        def gread(reader):
            return [reader.get() for _ in xrange(2)]
        gw1 = gevent.spawn(gwrite, self.wh, m)
        gw2 = gevent.spawn(gwrite, self.wh, m)
        gr = gevent.spawn(gread, self.rh)
        t = gr.get()
        assert [m, m] == t

    @raises(GPipeError)
    def test_twoclose(self):
        self.wh.close()
        self.wh.close()

    @raises(GPipeError)
    def test_closewrite(self):
        self.wh.close()
        self.wh.put('')

    @raises(GPipeError)
    def test_closeread(self):
        self.rh.close()
        self.rh.get()

    @raises(GPipeError)
    def test_readclose(self):
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self._greenlets_to_be_killed.append(g)
        gevent.sleep(0.01)
        self.rh.close()

    @raises(EOFError)
    def test_closewrite_read(self):
        self.wh.close()
        self.rh.get()


class TestIPC():
    def setup(self):
        self.rh, self.wh = pipe()
        self.rh2, self.wh2 = pipe()
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
        m = [1] * 999999
        def child(r):
            t = r.get()
            assert t == m
        p = gpipe.start_process(self.rh, child)
        self.wh.put(m)
        p.join()

    def test_twochannels_singlemsg(self):
        m1 = "OK"
        m2 = "FOO"
        def child(r1, r2):
            t = r1.get()
            assert t == m1
            t = r2.get()
            assert t == m2
        p = gpipe.start_process((self.rh, self.rh2), child)
        self.wh.put(m1)
        self.wh2.put(m2)
        p.join()

    def test_comm_in_child(self):
        m1 = "OK"
        m2 = "FOO"
        def child(r1, r2):
            # Receive first message from parent
            t = r1.get()
            assert t == m1
            # Test messaging between greenlets in child process
            local_reader, local_writer = pipe()
            testmsg = [1] * 999999
            def gwrite(writer):
                writer.put(testmsg)
            def gread(reader):
                return reader.get()
            gw = gevent.spawn(gwrite, local_writer)
            gr = gevent.spawn(gread, local_reader)
            t = gr.get()
            assert testmsg == t
            local_reader.close()
            local_writer.close()
            # Receive second message from parent
            t = r2.get()
            assert t == m2
            gw.join()
            gr.join()
        p = gpipe.start_process((self.rh, self.rh2), child)
        self.wh.put(m1)
        self.wh2.put(m2)
        p.join()

    @raises(GPipeError)
    def test_handler_after_transfer_to_child(self):
        def child(r):
            pass
        p = gpipe.start_process(self.rh, child)
        self.rh.close()
        p.join()

    def test_handler_in_nonregistered_process(self):
        def child(r):
            try:
                r.close()
            except GPipeError:
                return
            assert False
        p = multiprocessing.Process(target=child, args=(self.rh, ))
        p.start()
        p.join()
        self.rh.close()
