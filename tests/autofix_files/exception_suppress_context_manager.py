# ARG --exception-suppress-context-managers=mysuppress,*.dangerousname,dangerouslibrary.*
# ARG --enable=ASYNC910,ASYNC911

# AUTOFIX
# ASYNCIO_NO_AUTOFIX

# 912 is tested in eval_files/async912.py to avoid problems with autofix/asyncio

import contextlib
from contextlib import suppress
from typing import Any

import trio

mysuppress: Any
anything: Any
dangerouslibrary: Any


async def foo() -> Any:
    await foo()


async def foo_suppress():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with contextlib.suppress():
        await foo()
    await trio.lowlevel.checkpoint()


async def foo_suppress_1():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with mysuppress():
        await foo()
    await trio.lowlevel.checkpoint()


async def foo_suppress_2():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with anything.dangerousname():
        await foo()
    await trio.lowlevel.checkpoint()


async def foo_suppress_3():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with dangerouslibrary.anything():
        await foo()
    await trio.lowlevel.checkpoint()


# not enabled by default
# it probably wouldn't be too bad to track 'from contextlib import suppress'
async def foo_suppress_4():
    with suppress():
        await foo()


async def foo_suppress_async911():  # ASYNC911: 0, "exit", Statement("function definition", lineno)
    with contextlib.suppress():
        await foo()
        yield
        await foo()
    await trio.lowlevel.checkpoint()


# the `async with` checkpoints, so there's no error
async def foo_suppress_async():
    async with mysuppress:
        await foo()


async def foo_multiple():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with anything, contextlib.suppress():
        await foo()
    await trio.lowlevel.checkpoint()


# we only match on *calls*
async def foo_no_call():
    with contextlib.suppress:  # type: ignore[attr-defined]
        await foo()


# doesn't work on namedexpr, but those should use `as` anyway
async def foo_namedexpr():
    with (ref := contextlib.suppress()):
        await foo()


async def foo_suppress_as():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with contextlib.suppress() as my_suppressor:
        await foo()
    await trio.lowlevel.checkpoint()
