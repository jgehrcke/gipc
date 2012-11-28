.. gevent-ipc documentation master file, created by
   sphinx-quickstart on Thu Nov 22 15:14:51 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

GIPC: Multiprocessing and IPC for gevent
========================================

.. toctree::
   :maxdepth: 2


GIPC API
--------

Creating a pipe and its handle-pair
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: gipc
   :members: pipe


Handling handles
^^^^^^^^^^^^^^^^

.. autoclass:: gipc._GIPCHandle()
    :members: close

.. autoclass:: gipc._GIPCWriter()
    :show-inheritance:
    :members: put

.. autoclass:: gipc._GIPCReader()
    :show-inheritance:
    :members: get


Spawning child processes
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: gipc
    :members: start_process


Exception types
^^^^^^^^^^^^^^^

.. autoexception:: gipc.GIPCError

.. autoexception:: gipc.GIPCLocked

.. autoexception:: gipc.GIPCClosed


.. Indices and tables
.. ==================
..
.. * :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`

