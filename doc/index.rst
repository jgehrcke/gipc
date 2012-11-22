.. gevent-ipc documentation master file, created by
   sphinx-quickstart on Thu Nov 22 15:14:51 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

GIPC
====

.. toctree::
   :maxdepth: 2


GIPC API
--------

Creating a pipe and its handle-pair
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: gpipe
   :members: pipe


Handling handles
^^^^^^^^^^^^^^^^

.. autoclass:: gpipe._GPipeHandle()
    :members: close

.. autoclass:: gpipe._GPipeWriter()
    :show-inheritance:
    :members: put

.. autoclass:: gpipe._GPipeReader()
    :show-inheritance:
    :members: get


Spawning child processes
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: gpipe
    :members: start_process


Exception types
^^^^^^^^^^^^^^^

.. autoexception:: gpipe.GPipeError

.. autoexception:: gpipe.GPipeLocked

.. autoexception:: gpipe.GPipeClosed


.. Indices and tables
.. ==================
.. 
.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`

