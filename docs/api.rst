.. _api:

*************
API reference
*************

- :ref:`Spawning child processes <api_spawn>`
- :ref:`Creating a pipe and its handle-pair <api_pipe_create>`
- :ref:`Handling handles <api_handles>`
- :ref:`Controlling child processes <api_control_childs>`
- :ref:`Exception types <api_exceptions>`


.. _api_spawn:

Spawning child processes
========================

.. automodule:: gipc
    :members: start_process


.. _api_pipe_create:

Creating a pipe and its handle pair
===================================

.. automodule:: gipc
   :members: pipe


.. _api_handles:

Handling handles
================

.. autoclass:: gipc.gipc._GIPCHandle()
    :members: close

.. autoclass:: gipc.gipc._GIPCWriter()
    :show-inheritance:
    :members: put

.. autoclass:: gipc.gipc._GIPCReader()
    :show-inheritance:
    :members: get

.. autoclass:: gipc.gipc._GIPCDuplexHandle()


.. _api_control_childs:

Controlling child processes
===========================

.. autoclass:: gipc.gipc._GProcess()
    :show-inheritance:


.. _api_exceptions:

Exception types
===============

.. autoexception:: gipc.GIPCError

.. autoexception:: gipc.GIPCLocked

.. autoexception:: gipc.GIPCClosed
