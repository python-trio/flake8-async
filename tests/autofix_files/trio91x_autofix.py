# AUTOFIX
from __future__ import annotations

"""Docstring for file

So we make sure that import is added after it.
"""
# isort: skip_file
# ARG --enable=TRIO910,TRIO911

from typing import Any
import trio


def bar() -> Any:
    ...


async def foo() -> Any:
    await foo()


async def foo1():  # TRIO910: 0, "exit", Statement("function definition", lineno)
    bar()
    await trio.lowlevel.checkpoint()


async def foo_return():
    bar()
    await trio.lowlevel.checkpoint()
    return  # TRIO910: 4, "return", Statement("function definition", lineno-2)


async def foo_yield():  # TRIO911: 0, "exit", Statement("yield", lineno+2)
    bar()
    await trio.lowlevel.checkpoint()
    yield  # TRIO911: 4, "yield", Statement("function definition", lineno-2)
    await trio.lowlevel.checkpoint()


async def foo_if():
    if ...:
        await trio.lowlevel.checkpoint()
        return  # TRIO910: 8, "return", Statement("function definition", lineno-2)
    elif ...:
        await trio.lowlevel.checkpoint()
        return  # TRIO910: 8, "return", Statement("function definition", lineno-4)
    else:
        await trio.lowlevel.checkpoint()
        return  # TRIO910: 8, "return", Statement("function definition", lineno-6)


async def foo_while():
    await foo()
    while True:
        await trio.lowlevel.checkpoint()
        yield  # TRIO911: 8, "yield", Statement("yield", lineno)


async def foo_while2():
    await foo()
    while True:
        yield
        await foo()


async def foo_while3():
    await foo()
    while True:
        if ...:
            return
        await foo()


# check that multiple checkpoints don't get inserted
async def foo_while4():
    while True:
        if ...:
            await trio.lowlevel.checkpoint()
            yield  # TRIO911: 12, "yield", Statement("yield", lineno)  # TRIO911: 12, "yield", Statement("yield", lineno+2)  # TRIO911: 12, "yield", Statement("function definition", lineno-3)
        if ...:
            await trio.lowlevel.checkpoint()
            yield  # TRIO911: 12, "yield", Statement("yield", lineno)  # TRIO911: 12, "yield", Statement("yield", lineno-2)  # TRIO911: 12, "yield", Statement("function definition", lineno-5) # TRIO911: 12, "yield", Statement("yield", lineno-2)
            # this warns about the yield on lineno-2 twice, since it can arrive here from it in two different ways


# check state management of nested loops
async def foo_nested_while():
    while True:
        await trio.lowlevel.checkpoint()
        yield  # TRIO911: 8, "yield", Statement("function definition", lineno-2)
        while True:
            await trio.lowlevel.checkpoint()
            yield  # TRIO911: 12, "yield", Statement("yield", lineno-2)
            while True:
                await trio.lowlevel.checkpoint()
                yield  # TRIO911: 16, "yield", Statement("yield", lineno-2)  # TRIO911: 16, "yield", Statement("yield", lineno)


async def foo_while_nested_func():
    while True:
        await trio.lowlevel.checkpoint()
        yield  # TRIO911: 8, "yield", Statement("function definition", lineno-2) # TRIO911: 8, "yield", Statement("yield", lineno)

        async def bar():
            while ...:
                ...
            await foo()


# Code coverage: visitors run when inside a sync function that has an async function.
# When sync funcs don't contain an async func the body is not visited.
def sync_func():
    async def async_func():
        ...

    try:
        ...
    except:
        ...
    if ... and ...:
        ...
    while ...:
        if ...:
            continue
        break
    [... for i in range(5)]
    return
