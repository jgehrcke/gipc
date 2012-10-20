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
import os
import logging
import gevent
import gpipe

logging.basicConfig(format='%(asctime)-15s %(funcName)s# %(message)s')
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# on windows: messages per time:
# - independent of read buffer size


def reader(gpreader, N, msg):
    counter = 0
    while True:
        m = gpreader.get()
        if m != msg:
            raise Exception("wrong message received: %r" %  m)
        counter += 1
        if counter == N:
            break
    gpreader.close()

def writer(gpwriter, N, msg):
    for i in xrange(N):
        gpwriter.put(msg)
    gpwriter.close()

def main():
    N = 99999
    msg = "x"*100
    gpreader, gpwriter = gpipe.pipe(raw=False)
    gread = gevent.spawn(reader, gpreader, N, msg)
    gwrite = gevent.spawn(writer, gpwriter, N, msg)
    t1 = time.time()
    gwrite.join()
    gread.join()
    t2 = time.time()
    diff = t2-t1
    print "duration: %s" % diff
    mpertime = N/diff
    print "messages per second: %s" % mpertime


if __name__ == "__main__":
    main()
