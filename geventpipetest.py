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

"""
Example output for raw message transmission on Python 2.7.3
on Ubuntu 10.04 on a Xeon E5630 for
    N = 99999
    msg = "x"*10000+'\n'

18:24:19 $ python geventpipetest.py
2012-10-21 18:24:20,325 main# Pipe initialized.
2012-10-21 18:24:20,328 main# Read&write greenlets started.
2012-10-21 18:24:24,979 main# Read duration: 4.651 s
2012-10-21 18:24:24,979 main# Message transmission rate: 21501.776 msgs/s
2012-10-21 18:24:24,979 main# Data transfer rate: 205.077 MB/s
"""


import time
import logging
import gevent
import gpipe


logging.basicConfig(format='%(asctime)-15s %(funcName)s# %(message)s')
log = logging.getLogger()
log.setLevel(logging.DEBUG)


def main():
    N = 9999
    msg = "x"*100+'\n'
    gpreader, gpwriter = gpipe.pipe()
    log.info("Pipe initialized.")
    gwrite = gevent.spawn(writegreenlet, gpwriter, N, msg)
    gread = gevent.spawn(readgreenlet, gpreader, N, msg)
    log.info("Read&write greenlets started.")
    t1 = time.time()
    gread.join()
    t2 = time.time()
    tdiff = t2-t1
    mpertime = N/tdiff
    datasize_mb = float(len(msg)*N)/1024/1024
    datarate_mb = datasize_mb/tdiff
    log.info("Read duration: %.3f s" % tdiff)
    log.info("Message transmission rate: %.3f msgs/s" % mpertime)
    log.info("Data transfer rate: %.3f MB/s" % datarate_mb)
    gwrite.join()


def readgreenlet(gpreader, N, msg):
    for i in xrange(1, N+1):
        #m = gpreader.pickleget()
        m = gpreader.get(True)        
        if m != msg:
            raise Exception("Wrong message received: %r" %  m)
    gpreader.close()


def writegreenlet(gpwriter, N, msg):
    for i in xrange(N):
        #gpwriter.pickleput(msg)
        gpwriter.put(msg, True)        
    gpwriter.close()


if __name__ == "__main__":
    main()

