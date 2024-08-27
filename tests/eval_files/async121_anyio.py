# ASYNCIO_NO_ERROR # not a problem in asyncio
# TRIO_NO_ERROR # checked in async121.py
# BASE_LIBRARY anyio

import anyio


async def foo_return():
    async with anyio.create_task_group():
        return  # ASYNC121: 8, "return", "task group"


async def foo_return_nested():
    async with anyio.create_task_group():

        def bar():
            return  # safe


# continue
async def foo_while_continue_safe():
    async with anyio.create_task_group():
        while True:
            continue  # safe


async def foo_while_continue_unsafe():
    while True:
        async with anyio.create_task_group():
            continue  # ASYNC121: 12, "continue", "task group"


async def foo_for_continue_safe():
    async with anyio.create_task_group():
        for _ in range(5):
            continue  # safe


async def foo_for_continue_unsafe():
    for _ in range(5):
        async with anyio.create_task_group():
            continue  # ASYNC121: 12, "continue", "task group"


# break
async def foo_while_break_safe():
    async with anyio.create_task_group():
        while True:
            break  # safe


async def foo_while_break_unsafe():
    while True:
        async with anyio.create_task_group():
            break  # ASYNC121: 12, "break", "task group"


async def foo_for_break_safe():
    async with anyio.create_task_group():
        for _ in range(5):
            break  # safe


async def foo_for_break_unsafe():
    for _ in range(5):
        async with anyio.create_task_group():
            break  # ASYNC121: 12, "break", "task group"
