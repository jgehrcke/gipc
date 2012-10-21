"""
Compare different message reassembly methods performance-wise. For Python 2
and 3.
"""

from __future__ import print_function
import time
from random import randint
import itertools


try:
    xrange(3)
except NameError:
    xrange = range


def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]


N = 400
MINL = 10**2
MAXL = 2*10**6
CSIZE = 10**8 # extreme case
CSIZE = 65536 # Posix PIPE case
MESSAGES = ["x"*randint(MINL,MAXL)+'\n' for _ in xrange(N)]
ALLSTRING = ''.join(MESSAGES)
CHUNKS = [c for c in chunks(ALLSTRING, CSIZE)]


def main():
    print("N: %s\nMINL: %s\nMAXL: %s\nBUFFER: %s" % (N, MINL, MAXL, CSIZE))
    print("Messages blob set up. Start reassembling.")
    t1 = time.time()
    rebuilt = reassemble1()
    t2 = time.time()
    if rebuilt == MESSAGES:
        print("messages rebuilt.")
    diff = t2 - t1
    print("duration: %s" % diff)
    mpertime = N/diff
    datasize_mb = float(len(ALLSTRING))/1024/1024
    datarate_mb = datasize_mb/diff
    print("Message assembly rate: %.3f msgs/s" % mpertime)
    print("Data assembly rate: %.3f MB/s" % datarate_mb)


def reassemble1():
    """
Only good for large buffer sizes, much larger than pipe capacity.

Python 2.7.3 on Windows 7 on Intel P8800:
N: 400
MINL: 100
MAXL: 2000000
BUFFER: 65536
Messages blob set up. Start reassembling.
messages rebuilt.
duration: 3.6400001049
Message assembly rate: 109.890 msgs/s
Data assembly rate: 105.674 MB/s
Sun Oct 21 17:36:29 2012    profile

         24632 function calls in 4.315 seconds

   Ordered by: internal time
   List reduced from 11 to 8 due to restriction <8>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    3.051    3.051    3.647    3.647 msg_assembly_test.py:45(reassemble1) # this mainly is lines[0] = res + lines[0]
        1    0.625    0.625    4.277    4.277 msg_assembly_test.py:28(main)
     6155    0.560    0.000    0.560    0.000 {method 'splitlines' of 'str' objects}
        1    0.038    0.038    4.315    4.315 <string>:1(<module>)
     6155    0.015    0.000    0.015    0.000 {method 'endswith' of 'str' objects}
     6154    0.014    0.000    0.014    0.000 {method 'pop' of 'list' objects}
     6155    0.007    0.000    0.007    0.000 {method 'extend' of 'list' objects}
        6    0.005    0.001    0.005    0.001 {print}

Compares equally to method 2 on Windows/Python3 and on Linux test system.
    """
    messages = []
    res = ""
    for c in CHUNKS:
        lines = c.splitlines(True)       # costs a lot
        lines[0] = res + lines[0]        # baggabum. work with join!
        res = ''
        if not lines[-1].endswith('\n'): # costs nothing
            res = lines.pop()            # O(1), costs nothing
        messages.extend(lines)           # O(len(lines)), costs nothing
    return messages


def reassemble2():
    """
    Residue string concatenation only in case a message terminator is in newly
    read data. This method performs well for small and large chunk sizes.

Python 2.7.3 on Windows 7 on Intel P8800:
N: 400
MINL: 100
MAXL: 2000000
BUFFER: 65536
Messages blob set up. Start reassembling.
messages rebuilt.
duration: 0.80999994278
Message assembly rate: 493.827 msgs/s
Data assembly rate: 483.973 MB/s
Sun Oct 21 17:36:53 2012    profile

         38043 function calls in 1.464 seconds

   Ordered by: internal time
   List reduced from 13 to 8 due to restriction <8>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.617    0.617    1.425    1.425 msg_assembly_test.py:28(main)
     6273    0.477    0.000    0.477    0.000 {method 'splitlines' of 'str' objects}
      396    0.247    0.001    0.247    0.001 {method 'join' of 'str' objects}
        1    0.048    0.048    0.802    0.802 msg_assembly_test.py:85(reassemble2)
        1    0.038    0.038    1.464    1.464 <string>:1(<module>)
     6272    0.007    0.000    0.007    0.000 {method 'pop' of 'list' objects}
     6273    0.007    0.000    0.007    0.000 {method 'endswith' of 'str' objects}
     6272    0.006    0.000    0.006    0.000 {method 'append' of 'list' objects}
    """
    messages = []
    res = []
    for c in CHUNKS:
        data = c.splitlines(True)
        nlend = data[-1].endswith('\n')
        if res and (nlend or len(data) > 1):
            #res.append(data[0])
            #data[0] = ''.join(res)
            #data[0] = ''.join(itertools.chain.from_iterable([res, [data[0]]]))
            data[0] = ''.join(itertools.chain(res, [data[0]]))
            res = []
        if not nlend:
            res.append(data.pop())
        messages.extend(data)
    return messages


if __name__ == "__main__":
    import cProfile
    cProfile.run('main()', 'profile')
    import pstats
    p = pstats.Stats('profile')
    p.sort_stats('time').print_stats(8)
