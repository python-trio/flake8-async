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
- **TRIO101** `yield` inside a nursery or cancel scope is only safe when implementing a context manager - otherwise, it breaks exception handling.
