# ASYNCIO_NO_ERROR # checked in async121_asyncio.py

import trio
from typing import Any


# To avoid mypy unreachable-statement we wrap control flow calls in if statements
# they should have zero effect on the visitor logic.
def condition() -> bool:
    return False


def bar() -> Any: ...


async def foo_return():
    async with trio.open_nursery():
        if condition():
            return  # ASYNC121: 12, "return", "nursery"
        while condition():
            return  # ASYNC121: 12, "return", "nursery"

    return  # safe


async def foo_return_nested():
    async with trio.open_nursery():

        def bar():
            return  # safe

        async def bar():
            return  # safe


async def foo_while_safe():
    async with trio.open_nursery():
        while True:
            if condition():
                break  # safe
            if condition():
                continue  # safe
            continue  # safe


async def foo_while_unsafe():
    while True:
        async with trio.open_nursery():
            if condition():
                continue  # ASYNC121: 16, "continue", "nursery"
            if condition():
                break  # ASYNC121: 16, "break", "nursery"
        if condition():
            continue  # safe
        break  # safe


async def foo_for_safe():
    async with trio.open_nursery():
        for _ in range(5):
            if condition():
                continue  # safe
            if condition():
                break  # safe


async def foo_for_unsafe():
    for _ in range(5):
        async with trio.open_nursery():
            if condition():
                continue  # ASYNC121: 16, "continue", "nursery"
            if condition():
                break  # ASYNC121: 16, "break", "nursery"
        continue  # safe


async def foo_async_for_safe():
    async with trio.open_nursery():
        async for _ in bar():
            if condition():
                continue  # safe
            if condition():
                break  # safe


async def foo_async_for_unsafe():
    async for _ in bar():
        async with trio.open_nursery():
            if condition():
                continue  # ASYNC121: 16, "continue", "nursery"
            if condition():
                break  # ASYNC121: 16, "break", "nursery"
        continue  # safe


# nested nursery
async def foo_nested_nursery():
    async with trio.open_nursery():
        if condition():
            return  # ASYNC121: 12, "return", "nursery"
        async with trio.open_nursery():
            if condition():
                return  # ASYNC121: 16, "return", "nursery"
        if condition():
            return  # ASYNC121: 12, "return", "nursery"
    if condition():
        return  # safe
