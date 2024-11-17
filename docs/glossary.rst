********
Glossary
********

.. _cancel_scope:

cancel scope
------------
A cancel scope is a context manager which can request the library cancels
whatever task is executing in the body of the ``with`` (or ``async with``)
block.  A cancel scope is the key component of a :ref:`timeout context <timeout_context>`,
and used in :ref:`TaskGroups / Nurseries <taskgroup_nursery>` to cancel any remaining child tasks if one raises an
exception.

* Trio has an explicit :class:`trio.CancelScope` type, and `general documentation
  <https://trio.readthedocs.io/en/stable/reference-core.html#cancellation-and-timeouts>`__
  about cancellation and timeouts.

* AnyIO similarly has :class:`anyio.CancelScope` and `documentation
  <https://anyio.readthedocs.io/en/stable/cancellation.html>`__ of cancellation handling.

* asyncio does not have an explicit cancel-scope type, but incorporates similar semantics
  in :func:`asyncio.timeout` and :class:`asyncio.TaskGroup` and has `some documentation
  <https://docs.python.org/3/library/asyncio-task.html#task-cancellation>`__.


.. _timeout_context:

timeout context
---------------
A context manager that enforces a timeout on a block of code, by cancelling it
after a specified duration or at a preset time.  The timeout can also be
rescheduled after creation. They are internally implemented with a :ref:`cancel scope <cancel_scope>`,
which in anyio & trio can be directly initialized with a deadline.

* Trio has :func:`trio.move_on_after`, :func:`trio.move_on_at`,
  :func:`trio.fail_after`, :func:`trio.fail_at`, and :class:`trio.CancelScope`
  (`docs <https://trio.readthedocs.io/en/stable/reference-core.html#cancellation-and-timeouts>`__)

* AnyIO has :func:`anyio.move_on_after`, :func:`anyio.fail_after`, and :class:`anyio.CancelScope`
  (`docs <https://anyio.readthedocs.io/en/stable/cancellation.html>`__)

* asyncio has :func:`asyncio.timeout` and :func:`asyncio.timeout_at`
  (`docs <https://docs.python.org/3/library/asyncio-task.html#timeouts>`__)


.. _taskgroup_nursery:

TaskGroup / Nursery
-------------------

A collection of child Tasks that can run concurrently. Internally contains a
:ref:`cancel scope <cancel_scope>` for canceling any remaining child tasks if
one raises an exception.

* Trio has :class:`trio.Nursery`, created with :func:`trio.open_nursery`
  (`docs <https://trio.readthedocs.io/en/stable/reference-core.html#tasks-let-you-do-multiple-things-at-once>`__)

* AnyIO has  :class:`anyio.abc.TaskGroup`, created with :func:`anyio.create_task_group`
  (`docs <https://anyio.readthedocs.io/en/stable/tasks.html>`__)

* asyncio has :class:`asyncio.TaskGroup` since python 3.11
  (`docs <https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup>`__)


.. _cancellation:
.. _cancelled:

Cancelled / CancelledError
--------------------------

Handling cancellation is very sensitive, and you generally never want to catch a
cancellation exception without letting it propagate to the library.

General documentation on cancellation in the different async libraries:

* `Trio <https://trio.readthedocs.io/en/stable/reference-core.html#cancellation-and-timeouts>`__
* `AnyIO <https://anyio.readthedocs.io/en/stable/cancellation.html>`__
* `asyncio <https://docs.python.org/3/library/asyncio-task.html#task-cancellation>`__

Exception classes:

* :class:`trio.Cancelled`
* :func:`anyio.get_cancelled_exc_class`
* :class:`asyncio.CancelledError`

.. _checkpoint:

Checkpoint
----------
Checkpoints are points where the async backend checks for :ref:`cancellation <cancel_point>` and
:ref:`can switch which task is running <schedule_point>`, in an ``await``, ``async for``, or ``async with``
expression.  Regular checkpoints can be important for both performance and correctness.

Trio has extensive and detailed documentation on the concept of
:external+trio:ref:`checkpoints <checkpoints>`, and guarantees that all async
functions defined by Trio will either checkpoint or raise an exception when
``await``-ed. ``async for`` on Trio iterables will checkpoint before each
iteration, and when exhausting the iterator, and ``async with`` will checkpoint
on at least one of enter/exit.

The one exception is :func:`trio.open_nursery` and :func:`anyio.create_task_group` which are :ref:`schedule_points` but not :ref:`cancel_points`.

asyncio does not place any guarantees on if or when asyncio functions will
checkpoint. This means that enabling and adhering to :ref:`ASYNC91x <ASYNC910>`
will still not guarantee checkpoints on asyncio (even if used via anyio).

When using Trio (or an AnyIO library that people might use on Trio), it can be
very helpful to ensure that your own code adheres to the same guarantees as
Trio. For this we supply the :ref:`ASYNC91x <ASYNC910>` rules. To make it
possible to reason the rules will also assume that all other async functions
also adhere to those rules. This means you must be careful if you're using
3rd-party async libraries.

To insert a checkpoint with no other side effects, you can use
:func:`trio.lowlevel.checkpoint`/:func:`anyio.lowlevel.checkpoint`/:func:`asyncio.sleep(0)
<asyncio.sleep>`

.. _schedule_point:
.. _schedule_points:

Schedule Point
--------------
A schedule point is half of a full :ref:`checkpoint`, which allows the async backend to switch the running task, but doesn't check for cancellation (the other half is a :ref:`cancel_point`).
While you are unlikely to need one, they are available as :func:`trio.lowlevel.cancel_shielded_checkpoint`/:func:`anyio.lowlevel.cancel_shielded_checkpoint`, and equivalent to

.. code-block:: python

   from trio import CancelScope, lowlevel
   # or
   # from anyio import CancelScope, lowlevel

   with CancelScope(shield=True):
       await lowlevel.checkpoint()

asyncio does not have any direct equivalents due to their cancellation model being different.


.. _cancel_point:
.. _cancel_points:

Cancel Point
------------
A schedule point is half of a full :ref:`checkpoint`, which will raise :ref:`cancelled` if the enclosing cancel scope has been cancelled, but does not allow the scheduler to switch to a different task (the other half is a :ref:`schedule_point`).
While you are unlikely to need one, they are available as :func:`trio.lowlevel.checkpoint_if_cancelled`/:func:`anyio.lowlevel.checkpoint_if_cancelled`.
Users of asyncio might want to use :meth:`asyncio.Task.cancelled`.

.. _channel_stream_queue:

Channel / Stream / Queue
------------------------
Interfaces used for communicating between tasks, processes, the network, etc.

.. anyio streams is a :doc: and not a :label:, so we can't link with intersphinx :(

.. _anyio_streams: https://anyio.readthedocs.io/en/stable/streams.html#streams

* Trio has :ref:`channels <channels>` for python objects and :ref:`streams <abstract-stream-api>` for bytes.
* AnyIO has ``byte`` and ``object`` `streams <anyio_streams>`_
* asyncio has :ref:`queues <asyncio-queues>` for python objects and :ref:`streams <asyncio-streams>` for bytes.
