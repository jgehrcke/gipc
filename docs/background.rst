.. _background:

************************
Background & Terminology
************************

Understanding gipc requires familiarity with "event-driven", "asynchronous", and
"concurrent" architectures, with "coroutines", and especially with the gevent
Python libray and its underlying concepts. If you are new to some or any of that
the following paragraphs are my attempt to familiarize you with the topic.


I/O-bound: many execution units, and practically all of them wait
=================================================================

An event-driven architecture such as gevent's is tailored for an
input/output-bound (I/O-bound) computing scenario. In such a scenario there are
many (hundreds or thousands or many more) of individual execution units (think
"functions") whereas at any given time practically all of them wait for some
data to be delivered by an external source, through the operating system (e.g.
some input data that is expected to be incoming over the network, or some user
input provided via the keyboard).

That is, it is expected that practically all of these execution units are idle
at any given time. In other words, each execution unit spends the largest
fraction of its overall execution time (walltime of start of execution to
walltime of end of execution) *waiting* for *something*. It *cannot* proceed
until that *something* arrived. In the most general sense, each execution unit
spends most of its execution time waiting for one or more events (such as 'new
data has arrived for you!' or 'we completed sending the data to the other side
of the world over the network' or 'mouse button X was pressed').

In an ideal world the process of waiting for an event means literally doing
*nothing*, until notified to proceed. That is, while an execution unit waits for
an event to arrive it does not need to consume CPU time. However, surely, each
execution unit would like to proceed executing *immediately* once the event it
waited for has arrived.

These events are generally provided by the operating system through one of many
operating system-dependent event notification mechanisms. In general, it is the
responsibility of a so-called *event loop* to translate the operating system's
event notification system to the programming language-specific or
framework-specific notification system. In that sense, an event loop is the glue
between the operating system and the individual execution units.


Single-threaded event-driven architecture with coroutines
=========================================================

If such an architecture is implemented within a single operating system process
within just a single operating system thread then one can say with certainty
that the only activity that the execution units perform in parallel, i.e.
physically *simultaneously*, is *waiting*. That is quite an important insight!

Or, in other words: only a single execution unit is ever running (executing code
on a CPU core) at any given time.

In such an execution model you don't need to worry too much about the meanest
types of race conditions in your code because code from two (or more) execution
units is never run truly in parallel.

One of the easiest ways to reason about such an architecture is to think of the
individual execution units as *coroutines*, where each of the coroutines needs
to cooperate with a certain coroutine scheduling mechanism. The
cooperative scheduler is supposed to decide which coroutine should execute next.
It runs in the very same operating system thread as everything else. When it
runs, it has awareness of all the events the individual coroutines are waiting
for. Based on these data it decides which coroutine to run next (to
context-switch to).


Cooperative scheduling vs. preemptive scheduling
================================================

When the scheduler decides to run a coroutine, or to continue to execute a
previously interrupted coroutine then it **gives up control**: if that coroutine
decides to never yield control back to the scheduler then we can say that it
does *not* behave cooperatively. In that case the scheduler is out of luck:
there is no mechanism for it to *preemt* said coroutine. None of all the other
coroutines waiting for execution will ever be able to proceed. That is the major
difference between *cooperative scheduling* and *preemptive scheduling*. Cooperative scheduling can only make sense when there are no bad actors, and you are fully in control of the individual execution units. With the bad actor scenario in mind only preemptive scheduling can guarantee system availability (and that's why general-purpose operating systems such as Linux can preempt any given operating system thread at any time without further notice).

That is, once a coroutine has the honor to proceed to do something, it is
expected to be a good citizen, to cooperate, and to yield back control to the
scheduler as soon as in any way possible.

NodeJS is single-threaded, and the underlying event loop is libuv. The
asynchronous nature of the code is explicit and obvious from the code itself, as
of a callback-dominated code style.

Gevent is single-threaded, and the underlying event loop is libev. The
asynchronous nature of the code is implicit and not immediately obvious, because


The primary pattern used in gevent is the Greenlet, a lightweight coroutine
provided to Python as a C extension module. Greenlets all run inside of the OS
process for the main program but are scheduled cooperatively.

