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
    N = 5
    msg = "x"*100+'\n'
    gpreader, gpwriter = gpipe.pipe()
    log.info("Pipe initialized.")
    gwrite = gevent.spawn(writegreenlet, gpwriter, N, msg)
    gread = gevent.spawn(readgreenlet, gpreader, msg)
    gread2 = gevent.spawn(readgreenlet, gpreader, msg)
    log.info("Read&write greenlets started.")
    t1 = time.time()
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


def readgreenlet(gpreader, msg):
    counter = 0
    while True:
        m = gpreader.get()
        log.debug("m received: %s" % m)
        counter += 1
        #log.debug(m)
        if m == "STOP":
            log.info("stop received")
            break
        if m != msg:
            raise Exception("Wrong message received: %r" %  m)
        #gevent.sleep(0.001)
    log.info("Got %s messages." % counter)
    gpreader.close()


def writegreenlet(gpwriter, N, msg):
    for i in xrange(N):
        gpwriter.put(msg)
    gpwriter.put("STOP")
    log.debug("writer done.")
    gpwriter.close()


if __name__ == "__main__":
    main()

