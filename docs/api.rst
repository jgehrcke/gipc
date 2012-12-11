API
---

Creating a pipe and its handle-pair
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: gipc
   :members: pipe


Handling handles
^^^^^^^^^^^^^^^^

.. autoclass:: gipc.gipc._GIPCHandle()
    :members: close

.. autoclass:: gipc.gipc._GIPCWriter()
    :show-inheritance:
    :members: put

.. autoclass:: gipc.gipc._GIPCReader()
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
