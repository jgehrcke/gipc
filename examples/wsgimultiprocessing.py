# -*- coding: utf-8 -*-
# Copyright 2012-2021 Dr. Jan-Philip Gehrcke. See LICENSE file for details.


"""
This is a demonstration of what gipc and gevent can do in combination, not
necessarily a meaningful architecture for a production service :-).

Many HTTP clients (running in greenlets that concurrently run in a single child
process) each request an HTTP response from a simple HTTP server
(gevent.pywsgi.WSGIServer) running in the parent process.

In the HTTP server process every incoming HTTP request is handled in its own
greenlet. Each request-handling greenlet spawns a child process and asks it to
generate the HTTP response body for it (for simulating the case where HTTP
response body generation requires heavy lifting). The child process communicates
the payload back to the server process through a gipc pipe.

More precisely, a greenlet in the parent process, the `servelet`, runs the
`serve_forever` method. This dispatches each client connection to its own
greenlet running the `handle_http_request` function. This delegates the response
body generation to a child process which it launches for that purpose. The child
process transfers the response body back to the greenlet in the parent process
via a gipc pipe. This writes the response to the client.

Each client greenlet validates the response and terminates.

Output on my test system: 100 clients were served within 0.43 s.
"""

import os
import time
try:
    import urllib.request as request
except ImportError:
    import urllib2 as request

import gevent
from gevent.pywsgi import WSGIServer

import gipc


DUMMY_PAYLOAD = b"YO"
N_HTTP_CLIENTS = 100


def child_msg_generator(pipewriter):
    """I am executed in a child process.

    I write some dummy payload to the write end of the pipe through which I
    am connected to my parent process. I terminate immediately after writing
    the message.
    """
    pipewriter.put(DUMMY_PAYLOAD)

def invoke_server_forever(http_server):
    """I am executed in a greenlet.

    It is my job to hang in the cooperatively blocking `serve_forever()`
    call to accept incoming connections. I only terminate when I am
    explicitly killed from the outside.
    """
    http_server.serve_forever()

def main():

    def handle_http_request(_, start_response):
        """I am executed in a greenlet whenever an HTTP request came in."""

        # Start constructing an HTTP response. Build the header first.
        start_response('200 OK', [('Content-Type', 'text/html')])

        # What would we like to respond to the client? Let's ask a worker
        # process to generate the HTTP response body for us. (When would we do
        # this in the real world? For example when response generation requires
        # significant CPU-bound work as in image processing or when compiling a
        # complex PDF document, ...). In cases like this the CPU-bound work can
        # severely impact the responsiveness of the HTTP server process.)
        with gipc.pipe() as (r, w):
            # Start the child process (each client connection makes the server
            # process spawn a child process!). Pass the write end of the pipe to
            # the child process.
            p = gipc.start_process(target=child_msg_generator, args=(w, ))
            # Read the message from the child process.
            body = r.get()
            # Reap child (call wait(), remove it from process table).
            p.join()
            assert p.exitcode == 0

        # Write HTTP response body.
        return [body]

    server = WSGIServer(('127.0.0.1', 0), handle_http_request, log=None)
    servelet = gevent.spawn(invoke_server_forever, server)

    # Wait for server to be bound to socket.
    while True:
        if server.address[1] != 0:
            break
        gevent.sleep(0.05)

    # Start a single child process which then invokes many HTTP clients
    # concurrently (where each HTTP client runs in its own greenlet, and opens
    # its own TCP connection to the HTTP server). Pass the server address to the
    # child process so that they know where to TCP-connect to.
    p = gipc.start_process(target=child_client_runner, args=(server.address, ))

    # Wait until the child process is done doing all its work. It terminates
    # only after all the HTTP clients it spawned concurrently have received HTTP
    # responses.
    p.join()
    print('Child process terminated. Exit code: %s' % (p.exitcode, ))
    assert p.exitcode == 0

    # All clients have been served. Terminate the greenlet which runs the HTTP
    # server (it currently blocks, cooperatively, in the `server_forerver()`
    # call and calling `kill()` raises an exception in that greenlet so that it
    # returns from that call).
    servelet.kill()
    servelet.join()


def child_client_runner(server_address):
    """I am executed in a child process.

    Run many HTTP clients, each in its own greenlet. Each HTTP client
        - establishes a TCP connection to the server running in the parent
        - sends an HTTP request through it
        - reads the HTTP response and validates the response body
    """

    def get():
        # Expected to throw an HTTPError when the response code is not 200.
        body = request.urlopen('http://%s:%s/' % server_address).read()
        assert body == DUMMY_PAYLOAD

    t0 = time.time()
    clients = [gevent.spawn(get) for _ in range(N_HTTP_CLIENTS)]

    # Wait until all `get()` greenlet instances have completed.
    gevent.joinall(clients, raise_error=True)
    duration = time.time() - t0
    print('%s HTTP clients served within %.2f s.' % (N_HTTP_CLIENTS, duration))


if __name__ == "__main__":

    # Call `urlopen` with `None` in the parent before forking. This works around
    # a special type of segfault in the child after fork on Darwin. Doh! See
    # https://bugs.python.org/issue27126 and
    # https://github.com/jgehrcke/gipc/issues/52
    try:
        request.urlopen(None)
    except AttributeError:
        pass

    main()
