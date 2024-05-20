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


.. _cancellation:
.. _cancelled:

Cancelled / CancelledError
--------------------------

Handling cancellation is very sensitive, and you generally never want to catch a cancellation exception without letting it propagate to the library.

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
Checkpoints are points where the async backend checks for cancellation and invokes scheduling checks. Possible checkpoints are ``await``, ``async for`` (before each iteration, and when exhausting the iterator), and ``async with`` (on at least one of enter/exit).

Trio has extensive and detailed documentation on the concept of :external+trio:ref:`checkpoints <checkpoints>`, and guarantees that all trio async functions will checkpoint (unless they raised an exception).

anyio does not currently have any documentation on checkpoints.

asyncio will checkpoint... ???

To make it easier to reason about checkpoints the :ref:`ASYNC91x <ASYNC910>` rules enforces the same rules as trio for your own project - i.e. all async functions must guarantee a checkpoint (or exception). To make it possible to reason the rules will also assume that all other async functions also adhere to those rules. This means you must be careful if you're using 3rd-party async libraries.


.. _channel_stream_queue:

Channel / Stream / Queue
------------------------
Interfaces used for communicating between tasks, processes, the network, etc.

.. anyio streams is a :doc: and not a :label:, so we can't link with intersphinx :(

.. _anyio_streams: https://anyio.readthedocs.io/en/stable/streams.html#streams

* Trio has :ref:`channels <channels>` for python objects and :ref:`streams <abstract-stream-api>` for bytes.
* AnyIO has ``byte`` and ``object`` `streams <anyio_streams>`_
* asyncio has :ref:`queues <asyncio-queues>` for python objects and :ref:`streams <asyncio-streams>` for bytes.
