API
---

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