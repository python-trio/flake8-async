# Changelog
*[CalVer, YY.month.patch](https://calver.org/)*

## 23.1.4
- TRIO114 no longer triggers on posonly args named "task_status"
- TRIO116 will now match on any attribute parameter named `.inf`, not just `math.inf`.
- TRIO900 now only checks `@asynccontextmanager`, not other decorators passed with --no-checkpoint-warning-decorators.

## 23.1.3
- Add TRIO240: usage of `os.path` in async function.
- Add TRIO900: ban async generators not decorated with known safe decorator

## 23.1.2
- Add TRIO230, TRIO231 - sync IO calls in async function

## 23.1.1
- Add TRIO210, TRIO211 - blocking sync call in async function, using network packages (requests, httpx, urllib3)
- Add TRIO220, TRIO221 - blocking sync call in async function, using subprocess or os.

## 22.12.5
- The `--startable-in-context-manager` and `--trio200-blocking-calls` options now handle spaces and newlines.
- Now compatible with  [flake8-noqa](https://pypi.org/project/flake8-noqa/)'s NQA102 and NQA103 checks.

## 22.12.4
- TRIO200 no longer warns on directly awaited calls

## 22.12.3
- Worked around configuration-parsing bug for TRIO200 warning (more to come)

## 22.12.2
- Add TRIO200: User-configured blocking sync call  in async function

## 22.12.1
- TRIO114 will now trigger on the unqualified name, will now only check the first parameter
  directly, and parameters to function calls inside that.
- TRIO113 now only supports names that are valid identifiers, rather than fnmatch patterns.
- Add TRIO115: Use `trio.lowlevel.checkpoint()` instead of `trio.sleep(0)`.

## 22.11.5
- Add TRIO116: `trio.sleep()` with >24 hour interval should usually be `trio.sleep_forever()`.

## 22.11.4
- Add TRIO114 Startable function not in `--startable-in-context-manager` parameter list.

## 22.11.3
- Add TRIO113, prefer `await nursery.start(...)` to `nursery.start_soon()` for compatible functions when opening a context manager

## 22.11.2
- TRIO105 now also checks that you `await`ed `nursery.start()`.

## 22.11.1
- TRIO102 is no longer skipped in (async) context managers, since it's not a missing-checkpoint warning.

## 22.9.2
- Fix a crash on nontrivial decorator expressions (calls, PEP-614) and document behavior.

## 22.9.1
- Add `--no-checkpoint-warning-decorators` option, to disable missing-checkpoint warnings for certain decorated functions.

## 22.8.8
- Fix false alarm on TRIO107 with checkpointing `try` and empty `finally`
- Fix false alarm on TRIO107&108 with infinite loops

## 22.8.7
- TRIO107+108 now ignores `asynccontextmanager`s, since both `__aenter__` and `__aexit__` should checkpoint. `async with` is also treated as checkpointing on both enter and exit.
- TRIO107 now completely ignores any function whose body consists solely of ellipsis, pass, or string constants.
- TRIO103, 107 and 108 now inspects `while` conditions and `for` iterables to avoid false alarms on a couple cases where the loop body is guaranteed to run at least once.

## 22.8.6
- TRIO103 now correctly handles raises in loops, i.e. `raise` in else is guaranteed to run unless there's a `break` in the body.

## 22.8.5
- Add TRIO111: Variable, from context manager opened inside nursery, passed to `start[_soon]` might be invalidly accesed while in use, due to context manager closing before the nursery. This is usually a bug, and nurseries should generally be the inner-most context manager.
- Add TRIO112: this single-task nursery could be replaced by awaiting the function call directly.

## 22.8.4
- Fix TRIO108 raising errors on yields in some sync code.
- TRIO109 now skips all decorated functions to avoid false alarms

## 22.8.3
- TRIO108 now gives multiple error messages; one for each path lacking a guaranteed checkpoint

## 22.8.2
- Merged TRIO108 into TRIO107
- TRIO108 now handles checkpointing in async iterators

## 22.8.1
- Added TRIO109: Async definitions should not have a `timeout` parameter. Use `trio.[fail/move_on]_[at/after]`
- Added TRIO110: `while <condition>: await trio.sleep()` should be replaced by a `trio.Event`.

## 22.7.6
- Extend TRIO102 to also check inside `except BaseException` and `except trio.Cancelled`
- Extend TRIO104 to also check for `yield`
- Update error messages on TRIO102 and TRIO103

## 22.7.5
- Add TRIO103: `except BaseException` or `except trio.Cancelled` with a code path that doesn't re-raise
- Add TRIO104: "Cancelled and BaseException must be re-raised" if user tries to return or raise a different exception.
- Added TRIO107: Async functions must have at least one checkpoint on every code path, unless an exception is raised
- Added TRIO108: Early return from async function must have at least one checkpoint on every code path before it.

## 22.7.4
- Added TRIO105 check for not immediately `await`ing async trio functions.
- Added TRIO106 check that trio is imported in a form that the plugin can easily parse.

## 22.7.3
- Added TRIO102 check for unsafe checkpoints inside `finally:` blocks

## 22.7.2
- Avoid `TRIO100` false-alarms on cancel scopes containing `async for` or `async with`.

## 22.7.1
- Initial release with TRIO100 and TRIO101
