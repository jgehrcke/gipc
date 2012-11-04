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
    msg = "x"*21000+'\n'

19:12:01 $ python geventpipetest_process.py
2012-10-21 19:12:04,199 main# Pipe initialized.
2012-10-21 19:12:04,204 main# Read greenlet and write process started.
2012-10-21 19:12:04,204 writeprocess# WRITE greenlet started from PID 28255
2012-10-21 19:12:04,209 readgreenlet# READ greenlet started from PID 28254
2012-10-21 19:12:09,667 main# Read duration: 5.459 s
2012-10-21 19:12:09,668 main# Message transmission rate: 18319.271 msgs/s
2012-10-21 19:12:09,668 main# Data transfer rate: 366.900 MB/s
"""


import os
import sys
import logging
import time
if sys.platform == 'win32':
    TIMER = time.clock
else:
    TIMER = time.time
from multiprocessing import Process, Condition

import gevent
import gpipe



logging.basicConfig(format='%(asctime)-15s %(funcName)s# %(message)s')
log = logging.getLogger()
log.setLevel(logging.DEBUG)

def writer_process(writer, condition, N):
    log.debug("write PID: %s" % os.getpid())    
    writer.post_fork()
    m = '0' * 9999
    condition.acquire()
    condition.notify()
    condition.release()
    for i in xrange(N):
        writer.pickleput(m)
    writer.pickleput('stop')  


def main():
    DELTA = 1      
        
    def test_pipespeed():
        reader, writer = gpipe.pipe()
        condition = Condition()
        elapsed = 0
        N = 1
        writer.pre_fork()  
        while elapsed < DELTA:
            N *= 2
            p = Process(target=writer_process, args=(writer, condition, N))        
            condition.acquire()
            p.start()
            condition.wait()
            condition.release()
            
            result = None
            t = TIMER()
            while result != 'stop':
                result = reader.pickleget()
            elapsed = TIMER() - t
            p.join()

        print N, 'objects passed through connection in',elapsed,'seconds'
        print 'average number/sec:', N/elapsed

    test_pipespeed()
    log.debug("should exit")
    sys.exit()



    N = 9999
    msg = "a"*90000
    gpreader, gpwriter = gpipe.pipe()
    log.info("Pipe initialized.")
    
    # Prepare file descriptor for transfer to subprocess on Windows.
    #gpwriter.pre_windows_process_inheritance()
    
    gpwriter.pre_fork()
    pwrite = Process(target=writeprocess, args=[gpwriter, N, msg])
    pwrite.start()
    log.info("Read greenlet and write process started.")

    # The readgreenlet has to be started after the Process above.
    # Otherwise, it runs in both, the main process and the
    # subprocess and tries to read from the pipe read end in
    # both processes. Dirty. Is there a neat way to detect such
    # condition?
    # Anyway, important rule: run subprocess before spawning
    # any greenlet.
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
    gpwriter.post_fork()
    for i in xrange(N):
        #gpwriter.put(msg, raw=True)
        gpwriter.pickleput(msg)   


def readgreenlet(gpreader, N, msg):
    log.debug("READ greenlet started from PID %s" % os.getpid())
    for i in xrange(1, N+1):
        #m = gpreader.get(raw=True)
        m = gpreader.pickleget()
        if m != msg:
            raise Exception("Wrong message received")
    gpreader.close()


def writegreenlet(gpwriter, N, msg):
    for i in xrange(N):
        #gpwriter.put(msg, raw=True)
        gpwriter.pickleput(msg)        
    gpwriter.close()


if __name__ == "__main__":
    main()

