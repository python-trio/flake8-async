#########
Changelog
#########

`CalVer, YY.month.patch <https://calver.org/>`_

25.5.3
======
- :ref:`ASYNC115 <async115>` and :ref:`ASYNC116 <async116>` now also checks kwargs.

25.5.2
======
- :ref:`ASYNC102 <async102>` and :ref:`ASYNC120 <async120>` no longer requires cancel scopes to have a timeout. `(issue #272) <https://github.com/python-trio/flake8-async/issues/272>`_
- Add :ref:`ASYNC400 <async400>` except-star-invalid-attribute.

25.5.1
======
- Fixed :ref:`ASYNC113 <async113>` false alarms if the ``start_soon`` calls are in a nursery cm that was closed before the yield point.

25.4.4
======
- :ref:`ASYNC900 <async900>` now accepts and recommends :func:`trio.as_safe_channel`.

25.4.3
======
- :ref:`ASYNC100 <async100>` can now autofix ``with`` statements with multiple items.
- Fixed a bug where multiple ``with`` items would not interact, leading to ASYNC100 and ASYNC9xx false alarms. `(issue #367) <https://github.com/python-trio/flake8-async/issues/367>`_

25.4.2
======
- Add :ref:`ASYNC125 <async125>` constant-absolute-deadline.

25.4.1
======
- Add match-case (structural pattern matching) support to ASYNC103, 104, 910, 911 & 912.

25.3.1
======
- Add except* support to ASYNC102, 103, 104, 120, 910, 911, 912.

25.2.3
=======
- No longer require ``flake8`` for installation... so if you require support for config files you must install ``flake8-async[flake8]``.

25.2.2
=======
- :ref:`ASYNC113 <async113>` now only triggers on ``trio.[serve_tcp, serve_ssl_over_tcp, serve_listeners, run_process]``, instead of accepting anything as the attribute base. (e.g. :func:`anyio.run_process` is not startable).

25.2.1
=======
- :ref:`ASYNC912 <async912>` and :ref:`ASYNC913 <async913>` will now trigger if there's no *cancel* points. This means that :func:`trio.open_nursery`/`anyio.create_task_group` will not silence them on their own, unless they're guaranteed to start tasks.

25.1.1
=======
- Add :ref:`ASYNC124 <async124>` async-function-could-be-sync
- :ref:`ASYNC91x <ASYNC910>` now correctly handles ``await()`` in parameter lists.
- Fixed a bug with :ref:`ASYNC91x <ASYNC910>` and nested empty functions.

24.11.4
=======
- :ref:`ASYNC100 <async100>` once again ignores :func:`trio.open_nursery` and :func:`anyio.create_task_group`, unless we find a call to ``.start_soon()``.

24.11.3
=======
- Revert :ref:`ASYNC100 <async100>` ignoring :func:`trio.open_nursery` and :func:`anyio.create_task_group` due to it not viewing ``.start_soon()`` as introducing a :ref:`cancel point <cancel_point>`.

24.11.2
=======
- Fix crash in ``Visitor91x`` on ``async with a().b():``.

24.11.1
=======
- :ref:`ASYNC100 <async100>` now ignores :func:`trio.open_nursery` and :func:`anyio.create_task_group`
  as cancellation sources, because they are :ref:`schedule points <schedule_point>` but not
  :ref:`cancellation points <cancel_point>`.
- :ref:`ASYNC101 <async101>` and :ref:`ASYNC119 <async119>` are now silenced for decorators in :ref:`transform-async-generator-decorators`.

24.10.2
=======
- :ref:`ASYNC102 <async102>` now also warns about ``await()`` inside ``__aexit__``.

24.10.1
=======
- Add :ref:`ASYNC123 <async123>` bad-exception-group-flattening.

24.9.5
======
- Fix crash when analyzing code with infinite loop inside context manager.

24.9.4
======
- Add :ref:`ASYNC122 <async122>` delayed-entry-of-relative-cancelscope.

24.9.3
======
- :ref:`ASYNC102 <async102>` and :ref:`ASYNC120 <async120>`:
  - handles nested cancel scopes
  - detects internal cancel scopes of nurseries as a way to shield&deadline
  - no longer treats :func:`trio.open_nursery` or :func:`anyio.create_task_group` as cancellation sources
  - handles the `shield` parameter to :func:`trio.fail_after` and friends (added in trio 0.27)

24.9.2
======
- Fix false alarm in :ref:`ASYNC113 <async113>` and :ref:`ASYNC121 <async121>` with sync functions nested inside an async function.


24.9.1
======
- Add :ref:`ASYNC121 <async121>` control-flow-in-taskgroup.

24.8.1
======
- Add config option :ref:`transform-async-generator-decorators`, to list decorators which
  suppress :ref:`ASYNC900 <async900>`.

24.6.1
======
- Add :ref:`ASYNC120 <async120>` await-in-except.
- Fix false alarm with :ref:`ASYNC102 <async102>` with function definitions inside finally/except.

24.5.6
======
- Make :ref:`ASYNC913 <async913>` disabled by default, as originally intended.

24.5.5
======
- Add :ref:`ASYNC300 <async300>` create-task-no-reference.

24.5.4
======
- Add :ref:`ASYNC913 <async913>`: Indefinite loop with no guaranteed checkpoint.
- Fix bugs in :ref:`ASYNC910 <async910>` and :ref:`ASYNC911 <async911>` autofixing where they sometimes didn't add a library import.
- Fix crash in :ref:`ASYNC911 <async911>` when trying to autofix a one-line ``while ...: yield``
- Add :ref:`exception-suppress-context-managers`. Contextmanagers that may suppress exceptions.
- :ref:`ASYNC91x <ASYNC910>` now treats checkpoints inside ``with contextlib.suppress`` as unreliable.

24.5.3
======
- Rename config option ``trio200-blocking-calls`` to :ref:`async200-blocking-calls`.
- ``trio200-blocking-calls`` is now deprecated.

24.5.2
======
- ASYNC101 now also warns on anyio & asyncio taskgroups.
- Fixed a bug where ASYNC101 and ASYNC91x would not recognize decorators with parameters directly imported. I.e. ``@fixture(...)`` will now suppress errors.

24.5.1
======
- Add ASYNC912: no checkpoints in with statement are guaranteed to run.
- ASYNC100 now properly treats async for comprehensions as checkpoints.
- ASYNC100 now supports autofixing on asyncio.

24.4.2
======
- Add ASYNC119: yield in contextmanager in async generator.

24.4.1
======
- ASYNC91X: fix internal error caused by multiple ``try/except`` incorrectly sharing state.

24.3.6
======
- ASYNC100 no longer triggers if a context manager contains a ``yield``.

24.3.5
======
- ASYNC102 (no await inside finally or critical except) no longer raises warnings for calls to ``aclose()`` on objects in trio/anyio code. See `(issue #156) <https://github.com/python-trio/flake8-async/issues/156>`_

24.3.4
======
- ASYNC110 (don't loop sleep) now also warns if looping ``[trio/anyio].lowlevel.checkpoint()``.

24.3.3
======
- Add ASYNC251: ``time.sleep()`` in async method.

24.3.2
======
- Add ASYNC250: blocking sync call ``input()`` in async method.

24.3.1
======
- Removed TRIO117, MultiError removed in trio 0.24.0
- Renamed the library from flake8-trio to flake8-async, to indicate the checker supports more than just ``trio``.
- Renamed all error codes from TRIOxxx to ASYNCxxx
- Renamed the binary from flake8-trio to flake8-async
- Lots of internal renaming.
- Added asyncio support for several error codes
- added ``--library``

23.5.1
======
- TRIO91X now supports comprehensions
- TRIO100 and TRIO91X now supports autofixing
- Renamed ``--enable-visitor-codes-regex`` to ``--enable``
- Added ``--disable``, ``--autofix`` and ``--error-on-autofix``

23.2.5
======
- Fix false alarms for ``@pytest.fixture``-decorated functions in TRIO101, TRIO910 and TRIO911

23.2.4
======
- Fix TRIO900 false alarm on nested functions
- TRIO113 now also works on ``anyio.TaskGroup``

23.2.3
======
- Fix ``get_matching_call`` when passed a single string as base. Resolves possibly several false alarms, TRIO210 among them.

23.2.2
======
- Rename TRIO107 to TRIO910, and TRIO108 to TRIO911, and making them optional by default.
- Allow ``@pytest.fixture()``-decorated async generators, since they're morally context managers
- Add support for checking code written against `AnyIO <https://anyio.readthedocs.io/en/stable>`_
- Add TRIO118: Don't assign the value of ``anyio.get_cancelled_exc_class()`` to a variable, since that breaks linter checks and multi-backend programs.

23.2.1
======
- TRIO103 and TRIO104 no longer triggers when ``trio.Cancelled`` has been handled in previous except handlers.
- Add TRIO117: Reference to deprecated ``trio.[NonBase]MultiError``; use ``[Base]ExceptionGroup`` instead.
- Add TRIO232: blocking sync call on file object.
- Add TRIO212: blocking sync call on ``httpx.Client`` object.
- Add TRIO222: blocking sync call to ``os.wait*``
- TRIO221 now also looks for ``os.posix_spawn[p]``

23.1.4
======
- TRIO114 avoids a false alarm on posonly args named "task_status"
- TRIO116 will now match on any attribute parameter named ``.inf``, not just ``math.inf``.
- TRIO900 now only checks ``@asynccontextmanager``, not other decorators passed with --no-checkpoint-warning-decorators.

23.1.3
======
- Add TRIO240: usage of ``os.path`` in async function.
- Add TRIO900: ban async generators not decorated with known safe decorator

23.1.2
======
- Add TRIO230, TRIO231 - sync IO calls in async function

23.1.1
======
- Add TRIO210, TRIO211 - blocking sync call in async function, using network packages (requests, httpx, urllib3)
- Add TRIO220, TRIO221 - blocking sync call in async function, using subprocess or os.

22.12.5
=======
- The ``--startable-in-context-manager`` and ``--trio200-blocking-calls`` options now handle spaces and newlines.
- Now compatible with  `flake8-noqa <https://pypi.org/project/flake8-noqa/>`_ NQA102 and NQA103 checks.

22.12.4
=======
- TRIO200 no longer warns on directly awaited calls

22.12.3
=======
- Worked around configuration-parsing bug for TRIO200 warning (more to come)

22.12.2
=======
- Add TRIO200: User-configured blocking sync call  in async function

22.12.1
=======
- TRIO114 will now trigger on the unqualified name, will now only check the first parameter
  directly, and parameters to function calls inside that.
- TRIO113 now only supports names that are valid identifiers, rather than fnmatch patterns.
- Add TRIO115: Use ``trio.lowlevel.checkpoint()`` instead of ``trio.sleep(0)``.

22.11.5
=======
- Add TRIO116: ``trio.sleep()`` with >24 hour interval should usually be ``trio.sleep_forever()``.

22.11.4
=======
- Add TRIO114 Startable function not in ``--startable-in-context-manager`` parameter list.

22.11.3
=======
- Add TRIO113, prefer ``await nursery.start(...)`` to ``nursery.start_soon()`` for compatible functions when opening a context manager

22.11.2
=======
- TRIO105 now also checks that you ``await``\ed ``nursery.start()``.

22.11.1
=======
- TRIO102 is no longer skipped in (async) context managers, since it's not a missing-checkpoint warning.

22.9.2
======
- Fix a crash on nontrivial decorator expressions (calls, :pep:`614`) and document behavior.

22.9.1
======
- Add ``--no-checkpoint-warning-decorators`` option, to disable missing-checkpoint warnings for certain decorated functions.

22.8.8
======
- Fix false alarm on TRIO107 with checkpointing ``try`` and empty ``finally``
- Fix false alarm on TRIO107&108 with infinite loops

22.8.7
======
- TRIO107+108 now ignores ``asynccontextmanager`s, since both `__aenter__`` and ``__aexit__`` should checkpoint. ``async with`` is also treated as checkpointing on both enter and exit.
- TRIO107 now completely ignores any function whose body consists solely of ellipsis, pass, or string constants.
- TRIO103, 107 and 108 now inspects ``while`` conditions and ``for`` iterables to avoid false alarms on a couple cases where the loop body is guaranteed to run at least once.

22.8.6
======
- TRIO103 now correctly handles raises in loops, i.e. ``raise`` in else is guaranteed to run unless there's a ``break`` in the body.

22.8.5
======
- Add TRIO111: Variable, from context manager opened inside nursery, passed to ``start[_soon]`` might be invalidly accessed while in use, due to context manager closing before the nursery. This is usually a bug, and nurseries should generally be the inner-most context manager.
- Add TRIO112: this single-task nursery could be replaced by awaiting the function call directly.

22.8.4
======
- Fix TRIO108 raising errors on yields in some sync code.
- TRIO109 now skips all decorated functions to avoid false alarms

22.8.3
======
- TRIO108 now gives multiple error messages; one for each path lacking a guaranteed checkpoint

22.8.2
======
- Merged TRIO108 into TRIO107
- TRIO108 now handles checkpointing in async iterators

22.8.1
======
- Added TRIO109: Async definitions should not have a ``timeout`` parameter. Use ``trio.[fail/move_on]_[at/after]``
- Added TRIO110: ``while <condition>: await trio.sleep()`` should be replaced by a ``trio.Event``.

22.7.6
======
- Extend TRIO102 to also check inside ``except BaseException`` and ``except trio.Cancelled``
- Extend TRIO104 to also check for ``yield``
- Update error messages on TRIO102 and TRIO103

22.7.5
======
- Add TRIO103: ``except BaseException`` or ``except trio.Cancelled`` with a code path that doesn't re-raise
- Add TRIO104: "Cancelled and BaseException must be re-raised" if user tries to return or raise a different exception.
- Added TRIO107: Async functions must have at least one checkpoint on every code path, unless an exception is raised
- Added TRIO108: Early return from async function must have at least one checkpoint on every code path before it.

22.7.4
======
- Added TRIO105 check for not immediately ``await`` ing async trio functions.
- Added TRIO106 check that trio is imported in a form that the plugin can easily parse.

22.7.3
======
- Added TRIO102 check for unsafe checkpoints inside ``finally:`` blocks

22.7.2
======
- Avoid ``TRIO100`` false-alarms on cancel scopes containing ``async for`` or ``async with``.

22.7.1
======
- Initial release with TRIO100 and TRIO101
