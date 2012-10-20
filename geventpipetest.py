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

import time
import logging
import gevent
import gpipe


logging.basicConfig(format='%(asctime)-15s %(funcName)s# %(message)s')
log = logging.getLogger()
log.setLevel(logging.DEBUG)


def main():
    N = 999
    msg = "x"*100
    gpreader, gpwriter = gpipe.pipe()
    log.info("Pipe initialized.")
    gwrite = gevent.spawn(writegreenlet, gpwriter, N, msg)
    gread = gevent.spawn(readgreenlet, gpreader, N, msg)
    log.info("Read&write greenlets started.")
    t1 = time.time()
    gread.join()
    t2 = time.time()
    diff = t2-t1
    mpertime = N/diff
    log.info("Read duration: %s s" % diff)
    log.info("Message transmission rate: %s msgs/s" % mpertime)
    gwrite.join()


def readgreenlet(gpreader, N, msg):
    for i in xrange(1, N+1):
        m = gpreader.get()
        if m != msg:
            raise Exception("Wrong message received: %r" %  m)
    gpreader.close()


def writegreenlet(gpwriter, N, msg):
    for i in xrange(N):
        gpwriter.put(msg)
    gpwriter.close()


if __name__ == "__main__":
    main()
