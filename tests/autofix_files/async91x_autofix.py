# AUTOFIX
# asyncio will raise the same errors, but does not have autofix available
# ASYNCIO_NO_AUTOFIX
from __future__ import annotations

"""Docstring for file

So we make sure that import is added after it.
"""
# isort: skip_file
# ARG --enable=ASYNC910,ASYNC911

from typing import Any
import trio


def bar() -> Any: ...


async def foo() -> Any:
    await foo()


async def foo1():  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    bar()
    await trio.lowlevel.checkpoint()


async def foo_return():
    bar()
    await trio.lowlevel.checkpoint()
    return  # ASYNC910: 4, "return", Statement("function definition", lineno-2)


async def foo_yield():  # ASYNC911: 0, "exit", Statement("yield", lineno+2)
    bar()
    await trio.lowlevel.checkpoint()
    yield  # ASYNC911: 4, "yield", Statement("function definition", lineno-2)
    await trio.lowlevel.checkpoint()


async def foo_if():
    if bar():
        await trio.lowlevel.checkpoint()
        return  # ASYNC910: 8, "return", Statement("function definition", lineno-2)
    elif bar():
        await trio.lowlevel.checkpoint()
        return  # ASYNC910: 8, "return", Statement("function definition", lineno-4)
    else:
        await trio.lowlevel.checkpoint()
        return  # ASYNC910: 8, "return", Statement("function definition", lineno-6)


async def foo_while():
    await foo()
    while True:
        await trio.lowlevel.checkpoint()
        yield  # ASYNC911: 8, "yield", Statement("yield", lineno)


async def foo_while2():
    await foo()
    while True:
        yield
        await foo()


async def foo_while3():
    await foo()
    while True:
        if bar():
            return
        await foo()


# check that multiple checkpoints don't get inserted
async def foo_while4():
    while True:
        if bar():
            await trio.lowlevel.checkpoint()
            yield  # ASYNC911: 12, "yield", Statement("yield", lineno)  # ASYNC911: 12, "yield", Statement("yield", lineno+2)  # ASYNC911: 12, "yield", Statement("function definition", lineno-3)
        if bar():
            await trio.lowlevel.checkpoint()
            yield  # ASYNC911: 12, "yield", Statement("yield", lineno)  # ASYNC911: 12, "yield", Statement("yield", lineno-2)  # ASYNC911: 12, "yield", Statement("function definition", lineno-5) # ASYNC911: 12, "yield", Statement("yield", lineno-2)
            # this warns about the yield on lineno-2 twice, since it can arrive here from it in two different ways


# check state management of nested loops
async def foo_nested_while():
    while True:
        await trio.lowlevel.checkpoint()
        yield  # ASYNC911: 8, "yield", Statement("function definition", lineno-2)
        while True:
            await trio.lowlevel.checkpoint()
            yield  # ASYNC911: 12, "yield", Statement("yield", lineno-2)
            while True:
                await trio.lowlevel.checkpoint()
                yield  # ASYNC911: 16, "yield", Statement("yield", lineno-2)  # ASYNC911: 16, "yield", Statement("yield", lineno)


async def foo_while_nested_func():
    while True:
        await trio.lowlevel.checkpoint()
        yield  # ASYNC911: 8, "yield", Statement("function definition", lineno-2) # ASYNC911: 8, "yield", Statement("yield", lineno)

        async def bar():
            while bar():
                ...
            await foo()


# Code coverage: visitors run when inside a sync function that has an async function.
# When sync funcs don't contain an async func the body is not visited.
def sync_func():
    async def async_func(): ...

    try:
        ...
    except:
        ...
    if bar() and bar():
        ...
    while ...:
        if bar():
            continue
        break
    [... for i in range(5)]
    return


# TODO: issue 240
async def livelocks():
    while True:
        ...


# this will autofix 910 by adding a checkpoint outside the loop, which doesn't actually
# help, and the method still isn't guaranteed to checkpoint in case bar() always returns
# True.
async def no_checkpoint():  # ASYNC910: 0, "exit", Statement("function definition", lineno)
    while bar():
        try:
            await foo("1")  # type: ignore[call-arg]
        except TypeError:
            ...
    await trio.lowlevel.checkpoint()
