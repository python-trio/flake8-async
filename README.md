[![Documentation](https://img.shields.io/badge/docs-read%20now-blue.svg)](https://flake8-async.readthedocs.io)
[![Latest PyPi version](https://img.shields.io/pypi/v/flake8-async.svg)](https://pypi.org/project/flake8-async)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/python-trio/flake8-async/main.svg)](https://results.pre-commit.ci/latest/github/python-trio/flake8-async/main)
[![Test coverage](https://codecov.io/gh/python-trio/flake8-async/branch/main/graph/badge.svg)](https://codecov.io/gh/python-trio/flake8-async)
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

## Rules
https://flake8-async.readthedocs.io/en/latest/rules.html
