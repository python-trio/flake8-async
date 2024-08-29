# ASYNCIO_NO_ERROR # checked in async121_asyncio.py
# ANYIO_NO_ERROR # checked in async121_anyio.py

import trio


def condition() -> bool:
    return False


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


# continue
async def foo_while_continue_safe():
    async with trio.open_nursery():
        while True:
            continue  # safe


async def foo_while_continue_unsafe():
    while True:
        async with trio.open_nursery():
            if condition():
                continue  # ASYNC121: 16, "continue", "nursery"
        continue  # safe


async def foo_for_continue_safe():
    async with trio.open_nursery():
        for _ in range(5):
            continue  # safe


async def foo_for_continue_unsafe():
    for _ in range(5):
        async with trio.open_nursery():
            if condition():
                continue  # ASYNC121: 16, "continue", "nursery"
        continue  # safe


# break
async def foo_while_break_safe():
    async with trio.open_nursery():
        while True:
            break  # safe


async def foo_while_break_unsafe():
    while True:
        async with trio.open_nursery():
            if condition():
                break  # ASYNC121: 16, "break", "nursery"
        continue  # safe


async def foo_for_break_safe():
    async with trio.open_nursery():
        for _ in range(5):
            break  # safe


async def foo_for_break_unsafe():
    for _ in range(5):
        async with trio.open_nursery():
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
