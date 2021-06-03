# -*- coding: utf-8 -*-
# Copyright 2012-2021 Dr. Jan-Philip Gehrcke. See LICENSE file for details.


"""
gipc example: TCP communication between a server in the parent process and
multiple clients in a child process:

1)  gevent's ``StreamServer`` is started in a greenlet within the initial
    (parent) process. For each connecting client, it receives one
    newline-terminated message and echoes it back.

2)  A child process is started using gipc. Its starting point is the function
    ``clientprocess``. There, N TCP clients are started concurrently from N
    greenlets.

3)  Each client sends one message, validates the echo response and terminates.

4)  The child process terminates.

5)  After the child process is joined in the parent, the server is killed.

6)  The server greenlet is joined.

Output on my test machine:
1000 clients served within 0.54 s.
"""


import gevent
from gevent.server import StreamServer
from gevent import socket
import gipc
import time
import sys


PORT = 1337
N_CLIENTS = 1000
MSG = "HELLO\n"


def serve(sock, addr):
    f = sock.makefile(mode='rw')
    f.write(f.readline())
    f.flush()
    f.close()


def server():
    ss = StreamServer(('localhost', PORT), serve).serve_forever()


def clientprocess():
    t0 = time.time()
    clients = [gevent.spawn(client) for _ in range(N_CLIENTS)]
    gevent.joinall(clients)
    duration = time.time() - t0
    print('%s clients served within %.2f s.' % (N_CLIENTS, duration))


def client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', PORT))
    f = sock.makefile(mode='wr')
    f.write(MSG)
    f.flush()
    assert f.readline() == MSG
    f.close()


if __name__ == "__main__":
    s = gevent.spawn(server)
    c = gipc.start_process(clientprocess)
    c.join()
    s.kill()
    s.join()
