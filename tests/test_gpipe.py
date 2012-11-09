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

    def teardown(self):
        try:
            self.rh.close()
        except GPipeError:
            pass
        try:
            self.wh.close()
        except GPipeError:
            pass

    def test_singlemsg_short_bin(self):
        m = "OK"
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self.wh.put(m)
        t = g.get()
        assert m == t
        assert type(m) == type(t)

    def test_singlemsg_short_list(self):
        m = [1]
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self.wh.put(m)
        t = g.get()
        assert m == t
        assert type(m) == type(t)

    def test_singlemsg_short_list_commontypes(self):
        mlist = [1, True, False, None, Exception]
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self.wh.put(mlist)
        tlist = g.get()
        for i, m in enumerate(mlist):
            assert m == tlist[i]
            assert type(m) == type(tlist[i])

    def test_singlemsg_long_bin(self):
        m = "OK" * 999999
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self.wh.put(m)
        t = g.get()
        assert m == t
        assert type(m) == type(t)

    def test_singlemsg_long_list(self):
        m = [1] * 999999
        g = gevent.spawn(lambda r: r.get(), self.rh)
        self.wh.put(m)
        t = g.get()
        assert m == t
        assert type(m) == type(t)

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
        assert type(m) == type(t)

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
        assert type(m) == type(t1)

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
        assert type(t[0]) == type(m)

    @raises(GPipeError)
    def test_twoclose(self):
        self.wh.close()
        self.wh.close()
