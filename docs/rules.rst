****************
List of rules
****************

.. Esp when writing short descriptions it'd be very handy to link to a glossary, instead of saying stuff like ``except BaseException/trio.Cancelled/anyio.get_cancelled_exc_class()/asyncio.exceptions.CancelledError``
   it also allows easier use of library-specific terminology without forcing people to know all libraries by heart.
   It should probably have it's own page in the long run

Glossary
========

.. _timeout_context:

timeout context
---------------
Colloquially referred to as a "Timeout" or "CancelScope". A context manager that enforces a timeout on a block of code. Trio/AnyIO timeout functions are implemented with a ``CancelScope``, but you can also directly use ``CancelScope`` as a context manager.

.. I find this to have excessive spacing before/after sublists. Probably requires CSS to fix?

* Trio

  * `Documentation <https://trio.readthedocs.io/en/stable/reference-core.html#cancellation-and-timeouts>`__

  * :class:`trio.CancelScope`, :func:`trio.move_on_after`, :func:`trio.move_on_at`, :func:`trio.fail_after`, :func:`trio.fail_at`

* AnyIO

  * `Documentation <https://anyio.readthedocs.io/en/stable/cancellation.html>`__

  * :class:`anyio.CancelScope`, :func:`anyio.move_on_after`, :func:`anyio.fail_after``

* asyncio

  * `Documentation <https://docs.python.org/3/library/asyncio-task.html#timeouts>`__

  * :func:`asyncio.timeout`, :func:`asyncio.timeout_at`

.. _taskgroup_nursery:

TaskGroup / Nursery
-------------------

A collection of child Tasks that can run concurrently.

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


General rules
=============



.. For some reason using :ref:`timeout_context` fails to find the reference, but :ref:`timeout_context <timeout_context>` works. I have no clue why

.. list-table::
   :widths: 1 18 40
   :header-rows: 1

   * - Code
     - Name
     - Message
   * - ASYNC100
     - scope-no-checkpoint
     - A :ref:`timeout_context <timeout_context>` does not contain any ``await`` statements.  This makes it pointless, as the timeout can only be triggered by a checkpoint. This check also allows ``yield`` statements, since checkpoints can happen in the caller we yield to.
   * - ASYNC101
     - yield-in-taskgroup-or-scope
     - ``yield`` inside a :ref:`TaskGroup/Nursery <taskgroup_nursery>` or :ref:`timeout_context <timeout_context>` is only safe when implementing a context manager - otherwise, it breaks exception handling.
   * - ASYNC102
     - await-in-finally-or-cancelled
     - ``await`` inside ``finally`` or :ref:`cancelled-catching <cancelled>` ``except:`` must have shielded cancelscope with timeout.
   * - ASYNC103
     - no-reraise-cancelled
     - :ref:`cancelled <cancelled>`-catching exception that does not reraise the exception.
   * - ASYNC104
     - cancelled-not-raised
     - :ref:`cancelled <cancelled>`-catching exception does not raise the exception. Triggered on ``return`` or raising a different exception.
   * - ASYNC105
     - missing-await
     - async trio function called without using ``await``
   * - ASYNC106
     - bad-async-library-import
     - trio/anyio/asyncio must be imported with ``import xxx`` for the linter to work.
   * - ASYNC109
     - async-function-with-timeout
     - Async function definition with a ``timeout`` parameter. In structured concurrency the caller should instead use :ref:`timeout context managers <timeout_context>`.
   * - ASYNC110
     - busy-wait
     - ``while ...: await [trio/anyio].sleep()`` should be replaced by a :class:`trio.Event`/:class:`anyio.Event`.
   * - ASYNC111
     - variable-from-cm-in-start-soon
     - Variable, from context manager opened inside nursery, passed to ``start[_soon]`` might be invalidly accessed while in use, due to context manager closing before the nursery. This is usually a bug, and nurseries should generally be the inner-most context manager.
   * - ASYNC112
     - useless-nursery
     - Nursery body with only a call to ``nursery.start[_soon]`` and not passing itself as a parameter can be replaced with a regular function call.
   * - ASYNC113
     - start-soon-in-aenter
     - Using ``nursery.start_soon`` in ``__aenter__`` doesn't wait for the task to begin. Consider replacing with ``nursery.start``.
   * - ASYNC114
     - startable-not-in-config
     - Startable function (i.e. has a ``task_status`` keyword parameter) not in ``--startable-in-context-manager`` parameter list, please add it so ASYNC113 can catch errors when using it.
   * - ASYNC115
     - sleep-zero
     - Replace ``[trio/anyio].sleep(0)`` with the more suggestive ``[trio/anyio].lowlevel.checkpoint()``.
   * - ASYNC116
     - long-sleep-not-forever
     - ``[trio/anyio].sleep()`` with >24 hour interval should usually be ``[trio/anyio].sleep_forever()``.
   * - ASYNC118
     - cancelled-class-saved
     - Don't assign the value of ``anyio.get_cancelled_exc_class()`` to a variable, since that breaks linter checks and multi-backend programs.
   * - ASYNC119
     - yield-in-cm-in-async-gen
     - ``yield`` in context manager in async generator is unsafe, the cleanup may be delayed until ``await`` is no longer allowed.

- **ASYNC100**: A ``with [trio/anyio].fail_after(...):`` or ``with [trio/anyio].move_on_after(...):`` context does not contain any ``await`` statements.  This makes it pointless, as the timeout can only be triggered by a checkpoint. This check also allows ``yield`` statements, since checkpoints can happen in the caller we yield to.

- **ASYNC101**: ``yield`` inside a :class:`trio.Nursery`/:class:`anyio.abc.TaskGroup`/:py:class:`asyncio.TaskGroup`, or in a timeout/cancel scope is only safe when implementing a context manager - otherwise, it breaks exception handling. See `this thread <https://discuss.python.org/t/preventing-yield-inside-certain-context-managers/1091/23>`_ for discussion of a future PEP. This has substantial overlap with :ref:`ASYNC119 <async119>`, which will warn on almost all instances of ASYNC101, but ASYNC101 is about a conceptually different problem that will not get resolved by `PEP 533 <https://peps.python.org/pep-0533/>`_.
- **ASYNC102**: It's unsafe to await inside ``finally:`` or ``except BaseException/trio.Cancelled/anyio.get_cancelled_exc_class()/asyncio.exceptions.CancelledError`` unless you use a shielded cancel scope with a timeout. This is currently not able to detect asyncio shields.
- **ASYNC103**: ``except`` :class:`BaseException`/:class:`trio.Cancelled`/:func:`anyio.get_cancelled_exc_class`/:class:`asyncio.CancelledError`, or a bare ``except:`` with a code path that doesn't re-raise. If you don't want to re-raise :class:`BaseException`, add a separate handler for :class:`trio.Cancelled`/:func:`anyio.get_cancelled_exc_class`/:class:`asyncio.CancelledError` before.
- **ASYNC104**: :class:`trio.Cancelled`/:func:`anyio.get_cancelled_exc_class`/:class:`asyncio.CancelledError`/:class:`BaseException` must be re-raised. The same as ASYNC103, except specifically triggered on ``return`` or a different exception being raised.
- **ASYNC105**: Calling a trio async function without immediately ``await``\ ing it. This is only supported with trio functions, but you can get similar functionality with a type-checker.
- **ASYNC106**: ``trio``/``anyio``/``asyncio`` must be imported with ``import trio``/``import anyio``/``import asyncio`` for the linter to work.
- **ASYNC109**: Async function definition with a ``timeout`` parameter - use ``[trio/anyio].[fail/move_on]_[after/at]`` instead.
- **ASYNC110**: ``while <condition>: await [trio/anyio].sleep()`` should be replaced by a ``[trio/anyio].Event``.
- **ASYNC111**: Variable, from context manager opened inside nursery, passed to ``start[_soon]`` might be invalidly accessed while in use, due to context manager closing before the nursery. This is usually a bug, and nurseries should generally be the inner-most context manager.
- **ASYNC112**: Nursery body with only a call to ``nursery.start[_soon]`` and not passing itself as a parameter can be replaced with a regular function call.
- **ASYNC113**: Using :meth:`trio.Nursery.start_soon` in ``__aenter__`` doesn't wait for the task to begin. Consider replacing with ``nursery.start``.
- **ASYNC114**: Startable function (i.e. has a ``task_status`` keyword parameter) not in ``--startable-in-context-manager`` parameter list, please add it so ASYNC113 can catch errors when using it.
- **ASYNC115**: Replace ``[trio/anyio].sleep(0)`` with the more suggestive ``[trio/anyio].lowlevel.checkpoint()``.
- **ASYNC116**: ``[trio/anyio].sleep()`` with >24 hour interval should usually be ``[trio/anyio].sleep_forever()``.
- **ASYNC118**: Don't assign the value of :func:`anyio.get_cancelled_exc_class` to a variable, since that breaks linter checks and multi-backend programs.

  .. _async119:

- **ASYNC119**: ``yield`` in context manager in async generator is unsafe, the cleanup may be delayed until ``await`` is no longer allowed. We strongly encourage you to read `PEP 533 <https://peps.python.org/pep-0533/>`_ and use `async with aclosing(...) <https://docs.python.org/3/library/contextlib.html#contextlib.aclosing>`_, or better yet avoid async generators entirely (see :ref:`ASYNC900 <async900>` ) in favor of context managers which return an iterable `channel (trio) <https://trio.readthedocs.io/en/stable/reference-core.html#channels>`_, `stream (anyio) <https://anyio.readthedocs.io/en/stable/streams.html#streams>`_, or `queue (asyncio) <https://docs.python.org/3/library/asyncio-queue.html>`_.

  .. TODO: use intersphinx(?) instead of having to specify full URL

Blocking sync calls in async functions
======================================

Note: 22X, 23X and 24X has not had asyncio-specific suggestions written.


- **ASYNC200**: User-configured error for blocking sync calls in async functions. Does nothing by default, see :ref:`async200-blocking-calls` for how to configure it.
- **ASYNC210**: Sync HTTP call in async function, use ``httpx.AsyncClient``. This and the other ASYNC21x checks look for usage of ``urllib3`` and ``httpx.Client``, and recommend using ``httpx.AsyncClient`` as that's the largest http client supporting anyio/trio.
- **ASYNC211**: Likely sync HTTP call in async function, use ``httpx.AsyncClient``. Looks for ``urllib3`` method calls on pool objects, but only matching on the method signature and not the object.
- **ASYNC212**: Blocking sync HTTP call on httpx object, use httpx.AsyncClient.
- **ASYNC220**: Sync process call in async function, use ``await nursery.start([trio/anyio].run_process, ...)``. ``asyncio`` users can use `asyncio.create_subprocess_[exec/shell] <https://docs.python.org/3/library/asyncio-subprocess.html>`_.
- **ASYNC221**: Sync process call in async function, use ``await [trio/anyio].run_process(...)``. ``asyncio`` users can use `asyncio.create_subprocess_[exec/shell] <https://docs.python.org/3/library/asyncio-subprocess.html>`_.
- **ASYNC222**: Sync ``os.*`` call in async function, wrap in ``await [trio/anyio].to_thread.run_sync()``. ``asyncio`` users can use `asyncio.loop.run_in_executor <https://docs.python.org/3/library/asyncio-subprocess.html>`_.
- **ASYNC230**: Sync IO call in async function, use ``[trio/anyio].open_file(...)``. ``asyncio`` users need to use a library such as `aiofiles <https://pypi.org/project/aiofiles/>`_, or switch to `anyio <https://github.com/agronholm/anyio>`_.
- **ASYNC231**: Sync IO call in async function, use ``[trio/anyio].wrap_file(...)``. ``asyncio`` users need to use a library such as `aiofiles <https://pypi.org/project/aiofiles/>`_, or switch to `anyio <https://github.com/agronholm/anyio>`_.
- **ASYNC232**: Blocking sync call on file object, wrap the file object in ``[trio/anyio].wrap_file()`` to get an async file object.
- **ASYNC240**: Avoid using ``os.path`` in async functions, prefer using ``[trio/anyio].Path`` objects. ``asyncio`` users should consider `aiopath <https://pypi.org/project/aiopath>`_ or `anyio <https://github.com/agronholm/anyio>`_.
- **ASYNC250**: Builtin ``input()`` should not be called from async function. Wrap in ``[trio/anyio].to_thread.run_sync()`` or ``asyncio.loop.run_in_executor()``.
- **ASYNC251**: ``time.sleep(...)`` should not be called from async function. Use ``[trio/anyio/asyncio].sleep(...)``.


Optional rules disabled by default
==================================

.. _async900:

- **ASYNC900**: Async generator without ``@asynccontextmanager`` not allowed. You might want to enable this on a codebase since async generators are inherently unsafe and cleanup logic might not be performed. See https://github.com/python-trio/flake8-async/issues/211 and https://discuss.python.org/t/using-exceptiongroup-at-anthropic-experience-report/20888/6 for discussion.
- **ASYNC910**: Exit or ``return`` from async function with no guaranteed checkpoint or exception since function definition. You might want to enable this on a codebase to make it easier to reason about checkpoints, and make the logic of ASYNC911 correct.
- **ASYNC911**: Exit, ``yield`` or ``return`` from async iterable with no guaranteed checkpoint since possible function entry (yield or function definition)
  Checkpoints are ``await``, ``async for``, and ``async with`` (on one of enter/exit).
- **ASYNC912**: A timeout/cancelscope has checkpoints, but they're not guaranteed to run. Similar to ASYNC100, but it does not warn on trivial cases where there is no checkpoint at all. It instead shares logic with ASYNC910 and ASYNC911 for parsing conditionals and branches.

Removed rules
================

- **TRIOxxx**: All error codes are now renamed ASYNCxxx
- **TRIO107**: Renamed to TRIO910
- **TRIO108**: Renamed to TRIO911
- **TRIO117**: "Don't raise or catch ``trio.[NonBase]MultiError``, prefer ``[exceptiongroup.]BaseExceptionGroup``." ``MultiError`` was removed in trio==0.24.0.
