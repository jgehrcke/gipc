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
import sys
import logging
import gevent
import gpipe
from multiprocessing import Process


logging.basicConfig(format='%(asctime)-15s %(funcName)s# %(message)s')
log = logging.getLogger()
log.setLevel(logging.DEBUG)


def main():
    N = 999
    msg = "x"*120000
    gpreader, gpwriter = gpipe.pipe()
    log.info("Pipe initialized.")
    
    # Prepare file descriptor for transfer to subprocess on Windows.
    gpwriter.pre_windows_process_inheritance()
    
    pwrite = Process(target=writeprocess, args=[gpwriter, N, msg])
    pwrite.start()
    log.info("Read greenlet and write process started.")

    # The readgreenlet has to be started after the Process above.
    # Otherwise, it runs in both, the main process and the
    # subprocess and tries to read from the pipe read file 
    # descriptor from both processes. Dirty. Is there a neat
    # way to detect such a collision?
    # Otherwise: important rule: run subprocess before spawning
    # ANY greenlet.
    gread = gevent.spawn(readgreenlet, gpreader, N, msg)
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
    pwrite.join()

    
def writeprocess(gpwriter, N, msg):
    log.debug("WRITE greenlet started from PID %s" % os.getpid())
    # Restore file descriptor after transfer to subprocess on Windows.
    gpwriter.post_windows_process_inheritance()
    gwrite = gevent.spawn(writegreenlet, gpwriter, N, msg)
    gwrite.join()


def readgreenlet(gpreader, N, msg):
    log.debug("READ greenlet started from PID %s" % os.getpid())
    for i in xrange(1, N+1):
        m = gpreader.get()
        if m != msg:
            raise Exception("Wrong message received")
    gpreader.close()


def writegreenlet(gpwriter, N, msg):
    for i in xrange(N):
        gpwriter.put(msg)
    gpwriter.close()


if __name__ == "__main__":
    main()

