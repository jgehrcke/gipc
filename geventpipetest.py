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


logging.basicConfig(
    format='%(asctime)s,%(msecs)-6.1f [%(process)-5d]%(funcName)s# %(message)s',
    datefmt='%H:%M:%S')
log = logging.getLogger()
log.setLevel(logging.DEBUG)


def main():
    N = 3
    msg = "x"*10
    gpreader, gpwriter = gpipe.pipe()
    log.info("Pipe initialized.")
    gwrite = gevent.spawn(writegreenlet, gpwriter, N, msg)
    gread = gevent.spawn(readgreenlet, gpreader, msg, gid=1)
    gread2 = gevent.spawn(readgreenlet, gpreader, msg, gid=2)
    log.info("Read&write greenlets started.")
    t1 = time.time()
    gevent.sleep(3)
    gpreader.close()
    gread.join()
    gread2.join()
    t2 = time.time()
    tdiff = t2-t1
    mpertime = N/tdiff
    datasize_mb = float(len(msg)*N)/1024/1024
    datarate_mb = datasize_mb/tdiff
    log.info("Read duration: %.3f s" % tdiff)
    log.info("Message transmission rate: %.3f msgs/s" % mpertime)
    log.info("Data transfer rate: %.3f MB/s" % datarate_mb)
    gwrite.join()
    gpreader.close()


def readgreenlet(gpreader, msg, gid):
    counter = 0
    while True:
        try:
            log.info("%s: Invoking get() ..." % gid)
            m = gpreader.get()
        except EOFError:
            log.info("%s: Pipe got closed." % gid)
            break
        log.info("%s: m received: %s" % (gid, m))
        counter += 1
        if m == "STOP":
            log.info("%s: stop received" % gid)
            break
        if m != msg:
            raise Exception("%s: Wrong message received: %r" %  (gid,m))
        gevent.sleep(1)
    log.info("%s: Got %s messages." % (gid, counter))


def writegreenlet(gpwriter, N, msg):
    for i in xrange(N):
        gpwriter.put(msg)
    gpwriter.put("STOP")
    log.debug("writer done.")
    #gpwriter.close()


if __name__ == "__main__":
    main()

