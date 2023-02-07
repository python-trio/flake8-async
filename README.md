# flake8-trio

A highly opinionated flake8 plugin for [Trio](https://github.com/python-trio/trio)-related problems.

This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.

It may well be too noisy for anyone with different opinions, that's OK.

It also supports the [anyio](https://github.com/agronholm/anyio) library.

Pairs well with flake8-bugbear.

## Installation

```console
pip install flake8-trio
```

## List of warnings

- **TRIO100**: a `with trio.fail_after(...):` or `with trio.move_on_after(...):`
  context does not contain any `await` statements.  This makes it pointless, as
  the timeout can only be triggered by a checkpoint.
- **TRIO101**: `yield` inside a nursery or cancel scope is only safe when implementing a context manager - otherwise, it breaks exception handling.
- **TRIO102**: it's unsafe to await inside `finally:` or `except BaseException/trio.Cancelled` unless you use a shielded
  cancel scope with a timeout.
- **TRIO103**: `except BaseException`, `except trio.Cancelled` or a bare `except:` with a code path that doesn't re-raise. If you don't want to re-raise `BaseException`, add a separate handler for `trio.Cancelled` before.
- **TRIO104**: `Cancelled` and `BaseException` must be re-raised - when a user tries to `return` or `raise` a different exception.
- **TRIO105**: Calling a trio async function without immediately `await`ing it.
- **TRIO106**: trio must be imported with `import trio` for the linter to work.
- **TRIO107**: Renamed to TRIO910
- **TRIO108**: Renamed to TRIO911
- **TRIO109**: Async function definition with a `timeout` parameter - use `trio.[fail/move_on]_[after/at]` instead
- **TRIO110**: `while <condition>: await trio.sleep()` should be replaced by a `trio.Event`.
- **TRIO111**: Variable, from context manager opened inside nursery, passed to `start[_soon]` might be invalidly accessed while in use, due to context manager closing before the nursery. This is usually a bug, and nurseries should generally be the inner-most context manager.
- **TRIO112**: nursery body with only a call to `nursery.start[_soon]` and not passing itself as a parameter can be replaced with a regular function call.
- **TRIO113**: using `nursery.start_soon` in `__aenter__` doesn't wait for the task to begin. Consider replacing with `nursery.start`.
- **TRIO114**: Startable function (i.e. has a `task_status` keyword parameter) not in `--startable-in-context-manager` parameter list, please add it so TRIO113 can catch errors when using it.
- **TRIO115**: Replace `trio.sleep(0)` with the more suggestive `trio.lowlevel.checkpoint()`.
- **TRIO116**: `trio.sleep()` with >24 hour interval should usually be`trio.sleep_forever()`.
- **TRIO117**: Don't raise or catch `trio.[NonBase]MultiError`, prefer `[exceptiongroup.]BaseExceptionGroup`. Even if Trio still raises `MultiError` for legacy code, it can be caught with `BaseExceptionGroup` so it's fully redundant.
- **TRIO118**: Don't assign the value of `anyio.get_cancelled_exc_class()` to a variable, since that breaks linter checks and multi-backend programs.

### Warnings for blocking sync calls in async functions
- **TRIO200**: User-configured error for blocking sync calls in async functions. Does nothing by default, see [`trio200-blocking-calls`](#trio200-blocking-calls) for how to configure it.
- **TRIO210**: Sync HTTP call in async function, use `httpx.AsyncClient`.
- **TRIO211**: Likely sync HTTP call in async function, use `httpx.AsyncClient`. Looks for `urllib3` method calls on pool objects, but only matching on the method signature and not the object.
- **TRIO212**: Blocking sync HTTP call on httpx object, use httpx.AsyncClient.
- **TRIO220**: Sync process call in async function, use `await nursery.start(trio.run_process, ...)`.
- **TRIO221**: Sync process call in async function, use `await trio.run_process(...)`.
- **TRIO222**: Sync `os.*` call in async function, wrap in `await trio.to_thread.run_sync()`.
- **TRIO230**: Sync IO call in async function, use `trio.open_file(...)`.
- **TRIO231**: Sync IO call in async function, use `trio.wrap_file(...)`.
- **TRIO232**: Blocking sync call on file object, wrap the file object in `trio.wrap_file()` to get an async file object.
- **TRIO240**: Avoid using `os.path` in async functions, prefer using `trio.Path` objects.


### Warnings disabled by default
- **TRIO900**: Async generator without `@asynccontextmanager` not allowed.
- **TRIO910**: exit or `return` from async function with no guaranteed checkpoint or exception since function definition.
- **TRIO911**: exit, yield or return from async iterable with no guaranteed checkpoint since possible function entry (yield or function definition)
  Checkpoints are `await`, `async for`, and `async with` (on one of enter/exit).

## Configuration
[You can configure `flake8` with command-line options](https://flake8.pycqa.org/en/latest/user/configuration.html),
but we prefer using a config file. The file needs to start with a section marker `[flake8]` and the following options are then parsed using flake8's config parser, and can be used just like any other flake8 options.

### `no-checkpoint-warning-decorators`
Specify a list of decorators to disable checkpointing checks for, turning off TRIO910 and TRIO911 warnings for functions decorated with any decorator matching any in the list. Matching is done with [fnmatch](https://docs.python.org/3/library/fnmatch.html). Defaults to disabling for `asynccontextmanager`.

Decorators-to-match must be identifiers or dotted names only (not PEP-614 expressions), and will match against the name only - e.g. `foo.bar` matches `foo.bar`, `foo.bar()`, and `foo.bar(args, here)`, etc.

For example:
```
no-checkpoint-warning-decorators =
  mydecorator,
  mydecoratorpackage.checkpointing_decorators.*,
  ign*,
  *.ignore,
```


### `startable-in-context-manager`
Comma-separated list of methods which should be used with `.start()` when opening a context manager,
in addition to the default `trio.run_process`, `trio.serve_tcp`, `trio.serve_ssl_over_tcp`, and
`trio.serve_listeners`.  Names must be valid identifiers as per `str.isidentifier()`. For example:
```
startable-in-context-manager =
  myfun,
  myfun2,
```

### `trio200-blocking-calls`
Comma-separated list of pairs of values separated by `->` (optional whitespace stripped), where the first is a pattern for a call that should raise an error if found inside an async function, and the second is what should be suggested to use instead. It uses fnmatch as per [`no-checkpoint-warning-decorators`](#no-checkpoint-warning-decorators) for matching. The part after `->` is not used by the checker other than when printing the error, so you could add extra info there if you want.

The format of the error message is `User-configured blocking sync call {0} in async function, consider replacing with {1}.`, where `{0}` is the pattern the call matches and `{1}` is the suggested replacement.

Example:
```ini
trio200-blocking-calls =
  my_blocking_call -> async.alternative,
  module.block_call -> other_function_to_use,
  common_error_call -> alternative(). But sometimes you should use other_function(). Ask joe if you're unsure which one,
  dangerous_module.* -> corresponding function in safe_module,
  *.dangerous_call -> .safe_call()
```
Specified patterns must not have parentheses, and will only match when the pattern is the name of a call, so given the above configuration
```python
async def my_function():
    my_blocking_call()  # this would raise an error
    x = my_blocking_call(a, b, c)  # as would this
    y = my_blocking_call  # but not this
    y()  # or this
    [my_blocking_call][0]()  # nor this

    def my_blocking_call():  # it's also safe to use the name in other contexts
        ...

    arbitrary_other_function(my_blocking_call=None)
```
