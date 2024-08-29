# ANYIO_NO_ERROR
# TRIO_NO_ERROR # checked in async121.py
# BASE_LIBRARY asyncio
# TaskGroup was added in 3.11, we run type checking with 3.9
# mypy: disable-error-code=attr-defined

import asyncio


async def foo_return():
    async with asyncio.TaskGroup():
        return  # ASYNC121: 8, "return", "task group"


async def foo_return_nested():
    async with asyncio.TaskGroup():

        def bar():
            return  # safe


# continue
async def foo_while_continue_safe():
    async with asyncio.TaskGroup():
        while True:
            continue  # safe


async def foo_while_continue_unsafe():
    while True:
        async with asyncio.TaskGroup():
            continue  # ASYNC121: 12, "continue", "task group"


async def foo_for_continue_safe():
    async with asyncio.TaskGroup():
        for _ in range(5):
            continue  # safe


async def foo_for_continue_unsafe():
    for _ in range(5):
        async with asyncio.TaskGroup():
            continue  # ASYNC121: 12, "continue", "task group"


# break
async def foo_while_break_safe():
    async with asyncio.TaskGroup():
        while True:
            break  # safe


async def foo_while_break_unsafe():
    while True:
        async with asyncio.TaskGroup():
            break  # ASYNC121: 12, "break", "task group"


async def foo_for_break_safe():
    async with asyncio.TaskGroup():
        for _ in range(5):
            break  # safe


async def foo_for_break_unsafe():
    for _ in range(5):
        async with asyncio.TaskGroup():
            break  # ASYNC121: 12, "break", "task group"
