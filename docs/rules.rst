*****
Rules
*****


General rules
=============

Our ``ASYNC1xx`` rules check for semantic problems ranging from fatal errors (e.g. 101),
to idioms for clearer code (e.g. 116).

_`ASYNC100` : cancel-scope-no-checkpoint
    A :ref:`timeout_context` does not contain any :ref:`checkpoints <checkpoint>`.
    This makes it pointless, as the timeout can only be triggered by a checkpoint.
    This check also treats ``yield`` as a checkpoint, since checkpoints can happen in the caller we yield to.
    See :ref:`ASYNC912 <async912>` which will in addition guarantee checkpoints on every code path.

ASYNC101 : yield-in-cancel-scope
    ``yield`` inside a :ref:`taskgroup_nursery` or :ref:`timeout_context` is only safe when implementing a context manager - otherwise, it breaks exception handling.
    See `this thread <https://discuss.python.org/t/preventing-yield-inside-certain-context-managers/1091/23>`_ for discussion of a future PEP.
    This has substantial overlap with :ref:`ASYNC119 <ASYNC119>`, which will warn on almost all instances of ASYNC101, but ASYNC101 is about a conceptually different problem that will not get resolved by `PEP 533 <https://peps.python.org/pep-0533/>`_.

_`ASYNC102` : await-in-finally-or-cancelled
    ``await`` inside ``finally`` or :ref:`cancelled-catching <cancelled>` ``except:`` must have shielded :ref:`cancel scope <cancel_scope>` with timeout.
    If not, the async call will immediately raise a new cancellation, suppressing the cancellation that was caught.
    See :ref:`ASYNC120 <async120>` for the general case where other exceptions might get suppressed.
    This is currently not able to detect asyncio shields.

ASYNC103 : no-reraise-cancelled
    :ref:`cancelled`-catching exception that does not reraise the exception.
    If you don't want to re-raise :class:`BaseException`, add a separate handler for :ref:`Cancelled` before.

ASYNC104 : cancelled-not-raised
    :ref:`Cancelled`-catching exception does not raise the exception.
    Triggered on ``return`` or raising a different exception.

ASYNC105 : missing-await
    async trio function called without using ``await``.
    This is only supported with trio functions, but you can get similar functionality with a type-checker.

ASYNC106 : bad-async-library-import
    trio/anyio/asyncio must be imported with ``import xxx`` for the linter to work.

ASYNC109 : async-function-with-timeout
    Async function definition with a ``timeout`` parameter.
    In structured concurrency the caller should instead use :ref:`timeout context managers <timeout_context>`.

ASYNC110 : async-busy-wait
    ``while ...: await [trio/anyio].sleep()`` should be replaced by a :class:`trio.Event`/:class:`anyio.Event`.

ASYNC111 : variable-from-cm-in-start-soon
    Variable, from context manager opened inside :ref:`taskgroup_nursery`, passed to ``start[_soon]`` might be invalidly accessed while in use, due to context manager closing before the nursery.
    This is usually a bug, and nurseries should generally be the inner-most context manager.

ASYNC112 : useless-nursery
    :ref:`taskgroup_nursery` body with only a call to ``.start[_soon]`` and not passing itself as a parameter can be replaced with a regular function call.

_`ASYNC113` : start-soon-in-aenter
    Using :meth:`~trio.Nursery.start_soon`/:meth:`~anyio.abc.TaskGroup.start_soon` in ``__aenter__`` doesn't wait for the task to begin.
    Consider replacing with :meth:`~trio.Nursery.start`/:meth:`~anyio.abc.TaskGroup.start`.

_`ASYNC114` : startable-not-in-config
    Startable function (i.e. has a ``task_status`` keyword parameter) not in :ref:`--startable-in-context-manager <--startable-in-context-manager>` parameter list, please add it so ASYNC113 can catch errors when using it.

ASYNC115 : async-zero-sleep
    Replace :func:`trio.sleep(0) <trio.sleep>`/:func:`anyio.sleep(0) <anyio.sleep>` with the more suggestive :func:`trio.lowlevel.checkpoint`/:func:`anyio.lowlevel.checkpoint`.

ASYNC116 : long-sleep-not-forever
    :func:`trio.sleep`/:func:`anyio.sleep` with >24 hour interval should usually be :func:`trio.sleep_forever`/:func:`anyio.sleep_forever`.

ASYNC118 : cancelled-class-saved
    Don't assign the value of :func:`anyio.get_cancelled_exc_class()` to a variable, since that breaks linter checks and multi-backend programs.

_`ASYNC119` : yield-in-cm-in-async-gen
   ``yield`` in context manager in async generator is unsafe, the cleanup may be delayed until ``await`` is no longer allowed.
   We strongly encourage you to read `PEP 533 <https://peps.python.org/pep-0533/>`_ and use `async with aclosing(...) <https://docs.python.org/3/library/contextlib.html#contextlib.aclosing>`_, or better yet avoid async generators entirely (see `ASYNC900`_ ) in favor of context managers which return an iterable :ref:`channel/stream/queue <channel_stream_queue>`.

_`ASYNC120` : await-in-except
    Dangerous :ref:`checkpoint` inside an ``except`` block.
    If this checkpoint is cancelled, the current active exception will be replaced by the ``Cancelled`` exception, and cannot be reraised later.
    This will not trigger when :ref:`ASYNC102 <ASYNC102>` does, and if you don't care about losing non-cancelled exceptions you could disable this rule.
    This is currently not able to detect asyncio shields.


Blocking sync calls in async functions
======================================

Our 2xx lint rules warn you to use the async equivalent for slow sync calls which
would otherwise block the event loop (and therefore cause performance problems,
or even deadlock).

.. _httpx.Client: https://www.python-httpx.org/api/#client
.. _httpx.AsyncClient: https://www.python-httpx.org/api/#asyncclient
.. _urllib3: https://github.com/urllib3/urllib3
.. _aiofiles: https://pypi.org/project/aiofiles/
.. _anyio: https://github.com/agronholm/anyio

_`ASYNC200` : blocking-configured-call
    User-configured error for blocking sync calls in async functions.
    Does nothing by default, see :ref:`async200-blocking-calls` for how to configure it.

ASYNC210 : blocking-http-call
    Sync HTTP call in async function, use `httpx.AsyncClient`_.
    This and the other :ref:`ASYNC21x <ASYNC211>` checks look for usage of `urllib3`_ and `httpx.Client`_, and recommend using `httpx.AsyncClient`_ as that's the largest http client supporting anyio/trio.

_`ASYNC211` : blocking-http-call-pool
    Likely sync HTTP call in async function, use `httpx.AsyncClient`_.
    Looks for `urllib3`_ method calls on pool objects, but only matching on the method signature and not the object.

ASYNC212 : blocking-http-call-httpx
    Blocking sync HTTP call on httpx object, use `httpx.AsyncClient`_.

ASYNC220 : blocking-create-subprocess
    Sync call to :class:`subprocess.Popen` (or equivalent) in async function, use :func:`trio.run_process`/:func:`anyio.run_process`/:ref:`asyncio.create_subprocess_[exec/shell] <asyncio-subprocess>` in a :ref:`taskgroup_nursery`.

ASYNC221 : blocking-run-process
    Sync call to :func:`subprocess.run` (or equivalent) in async function, use :func:`trio.run_process`/:func:`anyio.run_process`/:ref:`asyncio.create_subprocess_[exec/shell] <asyncio-subprocess>`.

ASYNC222 : blocking-process-wait
    Sync call to :func:`os.wait` (or equivalent) in async function, wrap in :func:`trio.to_thread.run_sync`/:func:`anyio.to_thread.run_sync`/:meth:`asyncio.loop.run_in_executor`.

ASYNC230 : blocking-open-call
    Sync call to :func:`open` in async function, use :func:`trio.open_file`/:func:`anyio.open_file`. ``asyncio`` users need to use a library such as `aiofiles`_, or switch to `anyio`_.

ASYNC231 : blocking-fdopen-call
    Sync call to :func:`os.fdopen` in async function, use :func:`trio.wrap_file`/:func:`anyio.wrap_file`. ``asyncio`` users need to use a library such as `aiofiles`_, or switch to `anyio`_.

ASYNC232 : blocking-file-call
    Blocking sync call on file object, wrap the file object in :func:`trio.wrap_file`/:func:`anyio.wrap_file` to get an async file object.

ASYNC240 : blocking-path-usage
    Avoid using :mod:`os.path` in async functions, prefer using :class:`trio.Path`/:class:`anyio.Path` objects. ``asyncio`` users should consider `aiopath <https://pypi.org/project/aiopath>`__ or `anyio`_.

ASYNC250 : blocking-input
    Builtin :func:`input` should not be called from async function.
    Wrap in :func:`trio.to_thread.run_sync`/:func:`anyio.to_thread.run_sync` or :meth:`asyncio.loop.run_in_executor`.

ASYNC251 : blocking-sleep
    :func:`time.sleep` should not be called from async function.
    Use :func:`trio.sleep`/:func:`anyio.sleep`/:func:`asyncio.sleep`.


Asyncio-specific rules
======================

Asyncio *encourages* structured concurrency, with :obj:`asyncio.TaskGroup`, but does not *require* it.
We therefore provide some additional lint rules for common problems - although we'd also recommend a
gradual migration to AnyIO, which is much less error-prone.

_`ASYNC300` : create-task-no-reference
    Calling :func:`asyncio.create_task` without saving the result. A task that isn't referenced elsewhere may get garbage collected at any time, even before it's done.
    Note that this rule won't check whether the variable the result is saved in is susceptible to being garbage-collected itself. See the asyncio documentation for best practices.
    You might consider instead using a :ref:`TaskGroup <taskgroup_nursery>` and calling :meth:`asyncio.TaskGroup.create_task` to avoid this problem, and gain the advantages of structured concurrency with e.g. better cancellation semantics.


Optional rules disabled by default
==================================

Our 9xx rules check for semantics issues, like 1xx rules, but are disabled by default due
to the higher volume of warnings.  We encourage you to enable them - without guaranteed
:ref:`checkpoint`\ s timeouts and cancellation can be arbitrarily delayed, and async
generators are prone to the problems described in :pep:`533`.

_`ASYNC900` : unsafe-async-generator
       Async generator without :func:`@asynccontextmanager <contextlib.asynccontextmanager>` not allowed.
       You might want to enable this on a codebase since async generators are inherently unsafe and cleanup logic might not be performed.
       See `#211 <https://github.com/python-trio/flake8-async/issues/211>`__ and https://discuss.python.org/t/using-exceptiongroup-at-anthropic-experience-report/20888/6 for discussion.

_`ASYNC910` : async-function-no-checkpoint
    Exit or ``return`` from async function with no guaranteed :ref:`checkpoint` or exception since function definition.
    You might want to enable this on a trio/anyio codebase to make it easier to reason about checkpoints, and make the logic of ASYNC911 correct.

_`ASYNC911` : async-generator-no-checkpoint
    Exit, ``yield`` or ``return`` from async iterable with no guaranteed :ref:`checkpoint` since possible function entry (``yield`` or function definition).

_`ASYNC912` : cancel-scope-no-guaranteed-checkpoint
    A timeout/cancelscope has :ref:`checkpoints <checkpoint>`, but they're not guaranteed to run.
    Similar to `ASYNC100`_, but it does not warn on trivial cases where there is no checkpoint at all.
    It instead shares logic with `ASYNC910`_ and `ASYNC911`_ for parsing conditionals and branches.

_`ASYNC913` : indefinite-loop-no-guaranteed-checkpoint
    An indefinite loop (e.g. ``while True``) has no guaranteed :ref:`checkpoint <checkpoint>`. This could potentially cause a deadlock.

.. _autofix-support:

Autofix support
===============
The following rules support :ref:`autofixing <autofix>`.
- :ref:`ASYNC100 <ASYNC100>`
- :ref:`ASYNC910 <ASYNC910>`
- :ref:`ASYNC911 <ASYNC911>`
- :ref:`ASYNC913 <ASYNC913>`

Removed rules
================

- **TRIOxxx**: All error codes are now renamed ASYNCxxx
- **TRIO107**: Renamed to TRIO910
- **TRIO108**: Renamed to TRIO911
- **TRIO117**: "Don't raise or catch ``trio.[NonBase]MultiError``, prefer ``[exceptiongroup.]BaseExceptionGroup``." ``MultiError`` was removed in trio==0.24.0.
