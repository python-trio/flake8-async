********
Glossary
********

.. _cancel_scope:

cancel scope
------------
A cancel scope is a context manager which can request the library cancels
whatever task is executing in the body of the ``with`` (or ``async with``)
block.  A cancel scope is the key component of a :ref:`timeout context <timeout_context>`, and used in :ref:`TaskGroups / Nurseries <taskgroup_nursery>` to cancel any remaining child tasks if one raises an
exception.  Trio and AnyIO have an explicit ``CancelScope`` type; in asyncio
they are implicit.

* Trio

  * `Documentation <https://trio.readthedocs.io/en/stable/reference-core.html#cancellation-and-timeouts>`__

  * :class:`trio.CancelScope`

* AnyIO

  * `Documentation <https://anyio.readthedocs.io/en/stable/cancellation.html>`__

  * :class:`anyio.CancelScope`

.. _timeout_context:

timeout context
---------------
A context manager that enforces a timeout on a block of code, by cancelling it
after a specified duration or at a preset time.  The timeout can also be
rescheduled after creation. They are internally implemented with a :ref:`cancel scope <cancel_scope>`, which in anyio & trio can be directly initialized with a deadline.

.. I find this to have excessive spacing before/after sublists. Probably requires CSS to fix?

* Trio

  * `Documentation <https://trio.readthedocs.io/en/stable/reference-core.html#cancellation-and-timeouts>`__

  * :func:`trio.move_on_after`, :func:`trio.move_on_at`, :func:`trio.fail_after`, :func:`trio.fail_at`, :class:`trio.CancelScope`

* AnyIO

  * `Documentation <https://anyio.readthedocs.io/en/stable/cancellation.html>`__

  * :func:`anyio.move_on_after`, :func:`anyio.fail_after`, :class:`anyio.CancelScope`

* asyncio

  * `Documentation <https://docs.python.org/3/library/asyncio-task.html#timeouts>`__

  * :func:`asyncio.timeout`, :func:`asyncio.timeout_at`

.. _taskgroup_nursery:

TaskGroup / Nursery
-------------------

A collection of child Tasks that can run concurrently. Internally contains a :ref:`cancel scope <cancel_scope>` for canceling any remaining child tasks if one raises an exception.

* Trio

  * `Documentation <https://trio.readthedocs.io/en/stable/reference-core.html#tasks-let-you-do-multiple-things-at-once>`__

  * :class:`trio.Nursery`, created with :func:`trio.open_nursery`
* AnyIO

  * `Documentation <https://anyio.readthedocs.io/en/stable/tasks.html>`__
  * :class:`anyio.abc.TaskGroup`, created with :func:`anyio.create_task_group`.
* asyncio

  * `Documentation <https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup>`__
  * :class:`asyncio.TaskGroup` (since python 3.11)


.. _cancelled:

Cancelled / CancelledError
--------------------------

Handling cancellation is very sensitive, and you generally never want to catch a cancellation exception without letting it propagate to the library.

  * Trio: :class:`trio.Cancelled`. `Documentation <https://trio.readthedocs.io/en/stable/reference-core.html#cancellation-and-timeouts>`__
  * AnyIO: :func:`anyio.get_cancelled_exc_class`. `Documentation <https://anyio.readthedocs.io/en/stable/cancellation.html>`__
  * asyncio: :class:`asyncio.CancelledError`. `Documentation <https://docs.python.org/3/library/asyncio-task.html#task-cancellation>`__

.. _checkpoint:

Checkpoint
----------
Checkpoints are ``await``, ``async for``, and ``async with`` (on one of enter/exit). TODO write more and link stuff

.. _channel_stream_queue:

Channel / Stream / Queue
------------------------
* Trio: `channel <https://trio.readthedocs.io/en/stable/reference-core.html#channels>`__
* AnyIO: `stream <https://anyio.readthedocs.io/en/stable/streams.html#streams>`__
* asyncio: `queue <https://docs.python.org/3/library/asyncio-queue.html>`__
