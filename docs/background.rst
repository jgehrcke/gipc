.. _background:

************************
Background & Terminology
************************

Understanding gipc requires familiarity with "event-driven", "asynchronous", and
"concurrent" architectures, with "coroutines", and especially with the gevent
Python library and its underlying concepts. If you are new to some or any of
that the following paragraphs are my attempt to familiarize you with the topic.


I/O-bound: many execution units, practically all of them wait at any given time
===============================================================================

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
units is never run truly in parallel (that does not mean that such an
architecture is race condition-free :-).

One of the established ways to reason about such an architecture is to think of
the individual execution units as *coroutines*, where each of the coroutines
needs to cooperate with a certain coroutine scheduling mechanism. The coroutine
scheduler is supposed to decide which coroutine should execute next. It runs in
the very same operating system thread as everything else. When it runs, it has
awareness of all the events the individual coroutines are waiting for. Based on
these data it decides which coroutine to run next (one can say that it decides
"which coroutine to context-switch into").


Cooperative scheduling vs. preemptive scheduling
================================================

When the scheduler decides to invoke a new coroutine, or to continue to execute
a previously interrupted coroutine then it **gives up control**: if that
coroutine decides to never yield control back to the scheduler then we can say
that it does *not* behave cooperatively. In that case the scheduler is out of
luck: there is no mechanism for it to *preempt* said coroutine. None of all the
other coroutines waiting for execution will ever be able to proceed. That is the
major difference between *cooperative scheduling* and *preemptive scheduling*.
Cooperative scheduling can only make sense when there are no bad actors, and you
are fully in control of the individual execution units (and even then it is hard
enough to make sure that all units cooperate). With the bad actor scenario in
mind only preemptive scheduling can guarantee system availability (and that is
why general-purpose operating systems such as Linux can preempt any given
operating system thread at any time without further notice).

That is, once a coroutine has the honor to proceed to do something, it is
expected to be a good citizen, to cooperate, and to yield back control to the
scheduler as soon as in any way possible. That is the deal!

The most trivial and at the same time most relevant example for an execution
unit that does not behave cooperatively is a function that calls a blocking
operating system call such as a `recv()` on a socket that has been opened in the
(default) blocking mode. In that case, the entire thread from which the system
call was initiated cannot proceed executing, and the coroutine scheduling
machinery immediately stops.


Given all of that -- what is gevent and why do we need gipc?
============================================================

Gevent uses the wonderful libev as its underlying event loop library so that it
can efficiently interact with the operating system. Gevent makes use of the
magical greenlet project for implementing coroutines (then called "greenlets")
that can be context-switched into and out of highly efficiently. Gevent
implements the *gevent hub* which is the coroutine scheduler directly tied to a
libev event loop.

And then, after all, the majority of the dirty business and work done by gevent
is to magically make all relevant Python standard library modules behave
*cooperatively*. That means that all standard library modules that use blocking
system calls are monkey-patched to use non-blocking variants of said calls. All
of them? Well, the multiprocessing module is especially complex and hard to
adopt, which is why gipc now provides a subset of its functionality, in a
gevent-cooperative fashion.


"Asynchronous" vs. "synchronous"
================================

I do not necessarily like these terms. I feel like there almost always is a way
to describe the situation a little more explicitly than these terms can provide.

"Asynchronous" usually means that a certain entity (maybe an execution unit?)
submits a task or job elsewhere, and then requests to be notified once the work
has been done (or in case an error occurred). In the time between submission and
completion the control flow can proceed elsewhere, doing some useful work
instead of just to wait.

Now, how does that relate to gevent? The typical hello world gevent application
is single-threaded (maybe except for a few details which do not matter for this
discussion). Code related to the underlying event loop executes in that thread.
Code related to the gevent hub executes in that thread. The architecture clearly
follows an "asynchronous" paradigm in the sense that if one greenlet waits for
e.g. data to arrive on a socket, the gevent hub switches to *another* greenlet
and allows it to proceed execution. The asynchronous nature of the code flow,
however, is *implicit* because the context switch between greenlets is nothing
the programmer notes down explicitly in application code. It cannot really be
seen when reading the application code. In fact, an event-driven asynchronous
application written with gevent basically looks the same as if it were not
event-driven. One might argue that it is rather hard to understand the code path
in a gevent application: think of the application code being laid out in the
typical two-dimensional fashion (the code plane, which is like writing on a
piece of paper) -- then the context-switching is performed magically by the
gevent machinery in a third dimension, like a machine that makes crazy leaps and
jumps across your code plane.

In gevent, basically every call into the standard library might result in the
current coroutine being interrupted and *some* other coroutine proceeding
execution.

NodeJS for example also implements a single-threaded event-driven architecture.
Its underlying event loop is libuv. The asynchronous nature of the code is more
explicit and obvious from the code itself, because callbacks are being used for
connecting the dots. Arguably, callback-dominated code isn't easy to follow
either.

More than one event loop? gipc!
===============================

With gipc it is easy to connect multiple processes, each running their own
thread and event loop.