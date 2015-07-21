# -*- coding: utf-8 -*-
# Copyright 2012-2015 Jan-Philip Gehrcke. See LICENSE file for details.


import gevent
import gipc


def main():
    with gipc.pipe() as (r, w):
        p = gipc.start_process(target=child_process, args=(r, ))
        wg = gevent.spawn(writegreenlet, w)
        try:
            p.join()
        except KeyboardInterrupt:
            wg.kill(block=True)
            p.terminate()
        p.join()


def writegreenlet(writer):
    while True:
        writer.put("written to pipe from a greenlet running in the main process")
        gevent.sleep(1)


def child_process(reader):
    while True:
        print("Child process got message from pipe:\n\t'%s'" % reader.get())


if __name__ == "__main__":
    main()
