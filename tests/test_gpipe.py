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
sys.path.insert(0, os.path.abspath('..'))
import gpipe


class TestPipe():
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
        self.r, self.w = gpipe.pipe()
    
    def teardown(self):
        self.r.close()
        self.w.close()
        
    def test_msg_short(self):
        m = "OK"
        self.w.put(m)
        t = self.r.get()
        assert m == t
    