# ASYNCIO_NO_ERROR # not a problem in asyncio
# ANYIO_NO_ERROR # checked in async121_anyio.py

import trio


async def foo_return():
    async with trio.open_nursery():
        return  # ASYNC121: 8, "return", "nursery"


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
            continue  # ASYNC121: 12, "continue", "nursery"


async def foo_for_continue_safe():
    async with trio.open_nursery():
        for _ in range(5):
            continue  # safe


async def foo_for_continue_unsafe():
    for _ in range(5):
        async with trio.open_nursery():
            continue  # ASYNC121: 12, "continue", "nursery"


# break
async def foo_while_break_safe():
    async with trio.open_nursery():
        while True:
            break  # safe


async def foo_while_break_unsafe():
    while True:
        async with trio.open_nursery():
            break  # ASYNC121: 12, "break", "nursery"


async def foo_for_break_safe():
    async with trio.open_nursery():
        for _ in range(5):
            break  # safe


async def foo_for_break_unsafe():
    for _ in range(5):
        async with trio.open_nursery():
            break  # ASYNC121: 12, "break", "nursery"
