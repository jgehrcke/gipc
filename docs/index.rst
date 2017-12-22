.. gipc documentation master file
   Copyright 2012-2017 Jan-Philip Gehrcke. See LICENSE file for details.

.. |br| raw:: html

   <br />

.. |space| raw:: html

   &nbsp;&nbsp;


########################################
gipc: child processes and IPC for gevent
########################################

.. rst-class:: byline

    `GitHub <https://github.com/jgehrcke/gipc>`_ |space| | |space|
    `PyPI <https://pypi.python.org/pypi/gipc>`_  |space| | |space|
    `Bitbucket (legacy) <https://bitbucket.org/jgehrcke/gipc>`_ |br|

.. raw:: html

   <hr />

gipc (pronunciation as in “gipsy”) is an open source Python library created by
`Jan-Philip Gehrcke <https://gehrcke.de>`_. It provides reliable child
process management and inter-process communication (IPC) in the context of
`gevent <https://github.com/gevent/gevent>`_.

gipc works on CPython 2.7/3.4/3.5/3.6. It requires gevent 1.2 and supports both,
Unix-like systems as well as Windows. On Unix-like systems, gipc also runs on
PyPy2.7 and PyPy3.

gipc is used by, among others,
`Quantopian's <https://www.quantopian.com>`_
`remote Python debugger <https://github.com/quantopian/qdb>`_,
`Ajenti <http://ajenti.org/>`_,
`Chronology <http://chronology.github.io>`_,
`gipcrpc <https://github.com/studio-ousia/gipcrpc>`_,
`NetCall <https://github.com/aglyzov/netcall>`_,
`PokeAlarm <https://github.com/PokeAlarm/PokeAlarm>`_,
`Wishbone <https://wishbone.readthedocs.io>`_,
and `GDriveFS <https://github.com/dsoprea/GDriveFS>`_.
Are you successfully applying gipc in your project? That is always great
to hear: please :ref:`drop me a line <contact>`!

This documentation applies to gipc |release|. It was built on |today|.


**Contents of this documentation:**

.. toctree::
    :maxdepth: 1

    overview
    usage
    when
    challenges
    archnotes
    reliable
    winnotes
    examples
    api
    contact



.. - :ref:`Usage <usage>`
.. - :ref:`Which problem does gipc address, specifically? <what>`
.. - :ref:`Architecture notes <archnotes>`
.. - :ref:`Is gipc reliable? <reliable>`
.. - :ref:`Download & installation <installation>`
.. - :ref:`Platform support <platforms>`
.. - :ref:`Notes for Windows users <winnotes>`
.. - :ref:`Author, license, contact <contact>`
.. - :ref:`Code examples <examples>`
.. - :ref:`API documentation <api>`
..     - :ref:`Spawning child processes <api_spawn>`
..     - :ref:`Creating a pipe and its handle-pair <api_pipe_create>`
..     - :ref:`Handling handles <api_handles>`
..     - :ref:`Controlling child processes <api_control_childs>`
..     - :ref:`Exception types <api_exceptions>`



.. Indices and tables
.. ==================
..
.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`
