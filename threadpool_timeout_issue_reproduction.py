# -*- coding: utf-8 -*-


import logging
logging.basicConfig(
  format='%(asctime)s,%(msecs)-6.1f [%(process)-5d]%(funcName)s# %(message)s',
  datefmt='%H:%M:%S')
log = logging.getLogger()
log.setLevel(logging.DEBUG)

import gevent
import time
import os

r, w = os.pipe()

class RoffelError(Exception):
    pass


def some_function():
    log.debug("Start.")
    try:
        result = os.read(r, 1)
    except:
        log.debug("exception: %r" % (sys.exc_info, ))
    log.debug("I'm doing this anyway.")
    return result


def readgreenlet(r):
    with gevent.Timeout(1, False):
        try:
            result = gevent.get_hub().threadpool.apply_e(BaseException, some_function)
            os.write(w, 'a')
        except gevent.Timeout, e:
            log.debug("timeout: %s" % e)
            return None
    return result

# Second message must be available immediately now.
g = gevent.spawn(readgreenlet, r)
log.debug("g.get(): %r" % g.get())
print os.read(r, 1)




