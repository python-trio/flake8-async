# flake8-trio

A highly opinionated flake8 plugin for Trio-related problems.

This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.

It may well be too noisy for anyone with different opinions, that's OK.

Pairs well with flake8-async and flake8-bugbear.

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
- **TRIO103**: `except BaseException` and `except trio.Cancelled` with a code path that doesn't re-raise. Note that any `raise` statements in loops are ignored since it's tricky to parse loop flow with `break`, `continue` and/or the zero-iteration case.
- **TRIO104**: `Cancelled` and `BaseException` must be re-raised - when a user tries to `return` or `raise` a different exception.
- **TRIO105**: Calling a trio async function without immediately `await`ing it.
- **TRIO106**: trio must be imported with `import trio` for the linter to work.
- **TRIO107**: Async functions must have at least one checkpoint on every code path, unless an exception is raised.
- **TRIO108**: Early return from async function must have at least one checkpoint on every code path before it, unless an exception is raised.
  Checkpoints are `await`, `async with` `async for`.
- **TRIO109**: Async function definition with a `timeout` parameter - use `trio.[fail/move_on]_[after/at]` instead
- **TRIO110**: `while <condition>: await trio.sleep()` should be replaced by a `trio.Event`.
