[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/python-trio/flake8-async/main.svg)](https://results.pre-commit.ci/latest/github/python-trio/flake8-async/main)
[![Checked with pyright](https://microsoft.github.io/pyright/img/pyright_badge.svg)](https://microsoft.github.io/pyright/)
# flake8-async

A highly opinionated flake8 plugin for problems related to [Trio](https://github.com/python-trio/trio), [AnyIO](https://github.com/agronholm/anyio), or [asyncio](https://docs.python.org/3/library/asyncio.html).

This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.

It may well be too noisy for anyone with different opinions, that's OK.

Pairs well with flake8-bugbear.

Some checks are incorporated into [ruff](https://github.com/astral-sh/ruff).

This plugin was previously known as flake8-trio, and there was a separate small plugin known as flake8-async for asyncio. But this plugin was a superset of the checks in flake8-async, and support for anyio was added, so it's now named flake8-async to more properly convey its usage. At the same time all error codes were renamed from TRIOxxx to ASYNCxxx, as was previously used by the old flake8-async.

## Installation

```console
pip install flake8-async
```

## List of warnings
- **ASYNC100**: A `with [trio/anyio].fail_after(...):` or `with [trio/anyio].move_on_after(...):`
  context does not contain any `await` statements.  This makes it pointless, as
  the timeout can only be triggered by a checkpoint. This check also allows `yield` statements, since checkpoints can happen in the caller we yield to.
- **ASYNC101**: `yield` inside a trio/anyio nursery or cancel scope is only safe when implementing a context manager - otherwise, it breaks exception handling.
- **ASYNC102**: It's unsafe to await inside `finally:` or `except BaseException/trio.Cancelled/anyio.get_cancelled_exc_class()/asyncio.exceptions.CancelledError` unless you use a shielded cancel scope with a timeout. This is currently not able to detect asyncio shields.
- **ASYNC103**: `except BaseException/trio.Cancelled/anyio.get_cancelled_exc_class()/asyncio.exceptions.CancelledError`, or a bare `except:` with a code path that doesn't re-raise. If you don't want to re-raise `BaseException`, add a separate handler for `trio.Cancelled`/`anyio.get_cancelled_exc_class()`/`asyncio.exceptions.CancelledError` before.
- **ASYNC104**: `trio.Cancelled`/`anyio.get_cancelled_exc_class()`/`asyncio.exceptions.CancelledError`/`BaseException` must be re-raised. The same as ASYNC103, except specifically triggered on `return` or a different exception being raised.
- **ASYNC105**: Calling a trio async function without immediately `await`ing it. This is only supported with trio functions, but you can get similar functionality with a type-checker.
- **ASYNC106**: `trio`/`anyio`/`asyncio` must be imported with `import trio`/`import anyio`/`import asyncio` for the linter to work.
- **ASYNC109**: Async function definition with a `timeout` parameter - use `[trio/anyio].[fail/move_on]_[after/at]` instead.
- **ASYNC110**: `while <condition>: await [trio/anyio].sleep()` should be replaced by a `[trio/anyio].Event`.
- **ASYNC111**: Variable, from context manager opened inside nursery, passed to `start[_soon]` might be invalidly accessed while in use, due to context manager closing before the nursery. This is usually a bug, and nurseries should generally be the inner-most context manager.
- **ASYNC112**: Nursery body with only a call to `nursery.start[_soon]` and not passing itself as a parameter can be replaced with a regular function call.
- **ASYNC113**: Using `nursery.start_soon` in `__aenter__` doesn't wait for the task to begin. Consider replacing with `nursery.start`.
- **ASYNC114**: Startable function (i.e. has a `task_status` keyword parameter) not in `--startable-in-context-manager` parameter list, please add it so ASYNC113 can catch errors when using it.
- **ASYNC115**: Replace `[trio/anyio].sleep(0)` with the more suggestive `[trio/anyio].lowlevel.checkpoint()`.
- **ASYNC116**: `[trio/anyio].sleep()` with >24 hour interval should usually be `[trio/anyio].sleep_forever()`.
- **ASYNC118**: Don't assign the value of `anyio.get_cancelled_exc_class()` to a variable, since that breaks linter checks and multi-backend programs.
- **ASYNC119**: `yield` in context manager in async generator is unsafe, the cleanup may be delayed until `await` is no longer allowed. We strongly encourage you to read PEP-533 and use `async with aclosing(...)`, or better yet avoid async generators entirely (see ASYNC900) in favor of context managers which return an iterable channel/queue.

### Warnings for blocking sync calls in async functions
Note: 22X, 23X and 24X has not had asyncio-specific suggestions written.
- **ASYNC200**: User-configured error for blocking sync calls in async functions. Does nothing by default, see [`async200-blocking-calls`](#async200-blocking-calls) for how to configure it.
- **ASYNC210**: Sync HTTP call in async function, use `httpx.AsyncClient`. This and the other ASYNC21x checks look for usage of `urllib3` and `httpx.Client`, and recommend using `httpx.AsyncClient` as that's the largest http client supporting anyio/trio.
- **ASYNC211**: Likely sync HTTP call in async function, use `httpx.AsyncClient`. Looks for `urllib3` method calls on pool objects, but only matching on the method signature and not the object.
- **ASYNC212**: Blocking sync HTTP call on httpx object, use httpx.AsyncClient.
- **ASYNC220**: Sync process call in async function, use `await nursery.start([trio/anyio].run_process, ...)`. `asyncio` users can use [`asyncio.create_subprocess_[exec/shell]`](https://docs.python.org/3/library/asyncio-subprocess.html).
- **ASYNC221**: Sync process call in async function, use `await [trio/anyio].run_process(...)`. `asyncio` users can use [`asyncio.create_subprocess_[exec/shell]`](https://docs.python.org/3/library/asyncio-subprocess.html).
- **ASYNC222**: Sync `os.*` call in async function, wrap in `await [trio/anyio].to_thread.run_sync()`. `asyncio` users can use [`asyncio.loop.run_in_executor`](https://docs.python.org/3/library/asyncio-subprocess.html).
- **ASYNC230**: Sync IO call in async function, use `[trio/anyio].open_file(...)`. `asyncio` users need to use a library such as [aiofiles](https://pypi.org/project/aiofiles/), or switch to [anyio](https://github.com/agronholm/anyio).
- **ASYNC231**: Sync IO call in async function, use `[trio/anyio].wrap_file(...)`. `asyncio` users need to use a library such as [aiofiles](https://pypi.org/project/aiofiles/), or switch to [anyio](https://github.com/agronholm/anyio).
- **ASYNC232**: Blocking sync call on file object, wrap the file object in `[trio/anyio].wrap_file()` to get an async file object.
- **ASYNC240**: Avoid using `os.path` in async functions, prefer using `[trio/anyio].Path` objects. `asyncio` users should consider [aiopath](https://pypi.org/project/aiopath) or [anyio](https://github.com/agronholm/anyio).
- **ASYNC250**: Builtin `input()` should not be called from async function. Wrap in `[trio/anyio].to_thread.run_sync()` or `asyncio.loop.run_in_executor()`.
- **ASYNC251**: `time.sleep(...)` should not be called from async function. Use `[trio/anyio/asyncio].sleep(...)`.

### Warnings disabled by default
- **ASYNC900**: Async generator without `@asynccontextmanager` not allowed. You might want to enable this on a codebase since async generators are inherently unsafe and cleanup logic might not be performed. See https://github.com/python-trio/flake8-async/issues/211 and https://discuss.python.org/t/using-exceptiongroup-at-anthropic-experience-report/20888/6 for discussion.
- **ASYNC910**: Exit or `return` from async function with no guaranteed checkpoint or exception since function definition. You might want to enable this on a codebase to make it easier to reason about checkpoints, and make the logic of ASYNC911 correct.
- **ASYNC911**: Exit, `yield` or `return` from async iterable with no guaranteed checkpoint since possible function entry (yield or function definition)
  Checkpoints are `await`, `async for`, and `async with` (on one of enter/exit).

### Removed Warnings
- **TRIOxxx**: All error codes are now renamed ASYNCxxx
- **TRIO107**: Renamed to TRIO910
- **TRIO108**: Renamed to TRIO911
- **TRIO117**: Don't raise or catch `trio.[NonBase]MultiError`, prefer `[exceptiongroup.]BaseExceptionGroup`. `MultiError` was removed in trio==0.24.0.

## Examples
### install and run through flake8
```sh
pip install flake8 flake8-async
flake8 .
```
### install and run with pre-commit
If you use [pre-commit](https://pre-commit.com/), you can use it with flake8-async by
adding the following to your `.pre-commit-config.yaml`:

```yaml
minimum_pre_commit_version: '2.9.0'
repos:
- repo: https://github.com/python-trio/flake8-async
  rev: 23.2.5
  hooks:
    - id: flake8-async
      # args: [--enable=ASYNC, --disable=ASYNC9, --autofix=ASYNC]
```

This is often considerably faster for large projects, because `pre-commit`
can avoid running `flake8-async` on unchanged files.


Afterwards, run
```sh
pip install pre-commit flake8-async
pre-commit run .
```
### install and run as standalone
If inside a git repository, running without arguments will run it against all `*.py` files in the repository.
```sh
pip install flake8-async
flake8-async
```
#### with autofixes
```sh
flake8-async --autofix=ASYNC
```
#### specifying source files
```sh
flake8-async my_python_file.py
```
##### zsh-only
```zsh
flake8-async **/*.py
```

## Configuration
[You can configure `flake8` with command-line options](https://flake8.pycqa.org/en/latest/user/configuration.html),
but we prefer using a config file. The file needs to start with a section marker `[flake8]` and the following options are then parsed using flake8's config parser, and can be used just like any other flake8 options.
Note that it's not currently possible to use a configuration file when running `flake8-async` standalone.

### `ValueError` when trying to `ignore` error codes in config file
Error codes with more than three letters are not possible to `ignore` in config files since flake8>=6, as flake8 tries to validate correct configuration with a regex. We have decided not to conform to this, as it would be a breaking change for end-users requiring them to update `noqa`s and configurations, we think the `ASYNC` code is much more readable than e.g. `ASYxxx`, and ruff does not enforce such a limit. The easiest option for users hitting this error is to instead use the `--disable` option as documented [below](#--disable). See further discussion and other workarounds in https://github.com/python-trio/flake8-async/issues/230

### `--enable`
Comma-separated list of error codes to enable, similar to flake8 --select but is additionally more performant as it will disable non-enabled visitors from running instead of just silencing their errors.

### `--disable`
Comma-separated list of error codes to disable, similar to flake8 --ignore but is additionally more performant as it will disable non-enabled visitors from running instead of just silencing their errors.

### `--autofix`
Comma-separated list of error-codes to enable autofixing for if implemented. Requires running as a standalone program. Pass `--autofix=ASYNC` to enable all autofixes.

### `--error-on-autofix`
Whether to also print an error message for autofixed errors.

### `--anyio`
Change the default library to be anyio instead of trio. If trio is imported it will assume both are available and print suggestions with [anyio/trio].

### `no-checkpoint-warning-decorators`
Comma-separated list of decorators to disable checkpointing checks for, turning off ASYNC910 and ASYNC911 warnings for functions decorated with any decorator matching any in the list. Matching is done with [fnmatch](https://docs.python.org/3/library/fnmatch.html). Defaults to disabling for `asynccontextmanager`.

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

### `async200-blocking-calls`
Comma-separated list of pairs of values separated by `->` (optional whitespace stripped), where the first is a pattern for a call that should raise an error if found inside an async function, and the second is what should be suggested to use instead. It uses fnmatch as per [`no-checkpoint-warning-decorators`](#no-checkpoint-warning-decorators) for matching. The part after `->` is not used by the checker other than when printing the error, so you could add extra info there if you want.

The format of the error message is `User-configured blocking sync call {0} in async function, consider replacing with {1}.`, where `{0}` is the pattern the call matches and `{1}` is the suggested replacement.

Example:
```ini
async200-blocking-calls =
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
