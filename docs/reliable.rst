.. _reliable:

*****************
Is gipc reliable?
*****************
gipc is developed with a strong focus on reliability and with best intentions in
mind. Although gipc handles a delicate combination of signals, threads, and
forking, I have observed it to work reliably. The unit test suite covers all of
gipc's features within a clean gevent environment, but also covers scenarios of
medium complexity. To my knowledge, gipc is being deployed in serious production
scenarios.

But still, generally, you should be aware of the fact that mixing any of fork,
threads, greenlets and an event loop library such as libev bears the potential
for various kinds of corner-case disasters. One could argue that ``fork()`` in
the context of libev without doing a clean ``exec`` in the child already *is*
broken design. However, many people would like to do exactly this and gipc's
basic approach has proven to work in such cases. Now it is up to you
to evaluate gipc in the context of your project -- please share your experience.
