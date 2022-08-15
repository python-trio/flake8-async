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
- **TRIO103**: `except BaseException` and `except trio.Cancelled` with a code path that doesn't re-raise.
- **TRIO104**: `Cancelled` and `BaseException` must be re-raised - when a user tries to `return` or `raise` a different exception.
- **TRIO105**: Calling a trio async function without immediately `await`ing it.
- **TRIO106**: trio must be imported with `import trio` for the linter to work.
- **TRIO107**: exit or `return` from async function with no guaranteed checkpoint or exception since function definition.
- **TRIO108**: exit, yield or return from async iterable with no guaranteed checkpoint since possible function entry (yield or function definition)
  Checkpoints are `await`, `async for`, and `async with` (on one of enter/exit).
- **TRIO109**: Async function definition with a `timeout` parameter - use `trio.[fail/move_on]_[after/at]` instead
- **TRIO110**: `while <condition>: await trio.sleep()` should be replaced by a `trio.Event`.
- **TRIO111**: Variable, from context manager opened inside nursery, passed to `start[_soon]` might be invalidly accesed while in use, due to context manager closing before the nursery. This is usually a bug, and nurseries should generally be the inner-most context manager.
- **TRIO112**: nursery body with only a call to `nursery.start[_soon]` and not passing itself as a parameter can be replaced with a regular function call.
