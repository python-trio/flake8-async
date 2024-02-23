[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/python-trio/flake8-trio/main.svg)](https://results.pre-commit.ci/latest/github/python-trio/flake8-trio/main)
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

- **ASYNC100**: A `with trio.fail_after(...):` or `with trio.move_on_after(...):`
  context does not contain any `await` statements.  This makes it pointless, as
  the timeout can only be triggered by a checkpoint.
- **ASYNC101**: `yield` inside a nursery or cancel scope is only safe when implementing a context manager - otherwise, it breaks exception handling.
- **ASYNC102**: It's unsafe to await inside `finally:` or `except BaseException/trio.Cancelled` unless you use a shielded
  cancel scope with a timeout.
- **ASYNC103**: `except BaseException`, `except trio.Cancelled` or a bare `except:` with a code path that doesn't re-raise. If you don't want to re-raise `BaseException`, add a separate handler for `trio.Cancelled` before.
- **ASYNC104**: `Cancelled` and `BaseException` must be re-raised - when a user tries to `return` or `raise` a different exception.
- **ASYNC105**: Calling a trio async function without immediately `await`ing it.
- **ASYNC106**: `trio`/`anyio` must be imported with `import trio`/`import anyio` for the linter to work.
- **ASYNC107**: Renamed to ASYNC910
- **ASYNC108**: Renamed to ASYNC911
- **ASYNC109**: Async function definition with a `timeout` parameter - use `trio.[fail/move_on]_[after/at]` instead
- **ASYNC110**: `while <condition>: await trio.sleep()` should be replaced by a `trio.Event`.
- **ASYNC111**: Variable, from context manager opened inside nursery, passed to `start[_soon]` might be invalidly accessed while in use, due to context manager closing before the nursery. This is usually a bug, and nurseries should generally be the inner-most context manager.
- **ASYNC112**: Nursery body with only a call to `nursery.start[_soon]` and not passing itself as a parameter can be replaced with a regular function call.
- **ASYNC113**: Using `nursery.start_soon` in `__aenter__` doesn't wait for the task to begin. Consider replacing with `nursery.start`.
- **ASYNC114**: Startable function (i.e. has a `task_status` keyword parameter) not in `--startable-in-context-manager` parameter list, please add it so ASYNC113 can catch errors when using it.
- **ASYNC115**: Replace `trio.sleep(0)` with the more suggestive `trio.lowlevel.checkpoint()`.
- **ASYNC116**: `trio.sleep()` with >24 hour interval should usually be `trio.sleep_forever()`.
- **ASYNC117**: Don't raise or catch `trio.[NonBase]MultiError`, prefer `[exceptiongroup.]BaseExceptionGroup`. Even if Trio still raises `MultiError` for legacy code, it can be caught with `BaseExceptionGroup` so it's fully redundant.
- **ASYNC118**: Don't assign the value of `anyio.get_cancelled_exc_class()` to a variable, since that breaks linter checks and multi-backend programs.

### Warnings for blocking sync calls in async functions
- **ASYNC200**: User-configured error for blocking sync calls in async functions. Does nothing by default, see [`trio200-blocking-calls`](#trio200-blocking-calls) for how to configure it.
- **ASYNC210**: Sync HTTP call in async function, use `httpx.AsyncClient`.
- **ASYNC211**: Likely sync HTTP call in async function, use `httpx.AsyncClient`. Looks for `urllib3` method calls on pool objects, but only matching on the method signature and not the object.
- **ASYNC212**: Blocking sync HTTP call on httpx object, use httpx.AsyncClient.
- **ASYNC220**: Sync process call in async function, use `await nursery.start(trio.run_process, ...)`.
- **ASYNC221**: Sync process call in async function, use `await trio.run_process(...)`.
- **ASYNC222**: Sync `os.*` call in async function, wrap in `await trio.to_thread.run_sync()`.
- **ASYNC230**: Sync IO call in async function, use `trio.open_file(...)`.
- **ASYNC231**: Sync IO call in async function, use `trio.wrap_file(...)`.
- **ASYNC232**: Blocking sync call on file object, wrap the file object in `trio.wrap_file()` to get an async file object.
- **ASYNC240**: Avoid using `os.path` in async functions, prefer using `trio.Path` objects.


### Warnings disabled by default
- **ASYNC900**: Async generator without `@asynccontextmanager` not allowed.
- **ASYNC910**: Exit or `return` from async function with no guaranteed checkpoint or exception since function definition.
- **ASYNC911**: Exit, `yield` or `return` from async iterable with no guaranteed checkpoint since possible function entry (yield or function definition)
  Checkpoints are `await`, `async for`, and `async with` (on one of enter/exit).

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

### `--enable`
Comma-separated list of error codes to enable, similar to flake8 --select but is additionally more performant as it will disable non-enabled visitors from running instead of just silencing their errors.

### `--disable`
Comma-separated list of error codes to disable, similar to flake8 --ignore but is additionally more performant as it will disable non-enabled visitors from running instead of just silencing their errors.

### `--autofix`
Comma-separated list of error-codes to enable autofixing for if implemented. Requires running as a standalone program. Pass `--autofix=ASYNC` to enable all autofixes.

### `--error-on-autofix`
Whether to also print an error message for autofixed errors.

### `--anyio`
Change the default library to be anyio instead of trio. If trio is imported it will assume both are available and print suggestions with [anyio|trio].

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
