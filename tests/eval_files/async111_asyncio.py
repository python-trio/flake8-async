# main tests in async111.py
# this only tests asyncio.TaskGroup in particular
# BASE_LIBRARY asyncio
# ANYIO_NO_ERROR
# TRIO_NO_ERROR
# TaskGroup introduced in 3.11, we run typechecks with 3.9
# mypy: disable-error-code=attr-defined


import asyncio


async def bar(*args): ...


async def foo():
    async with asyncio.TaskGroup() as tg:
        with open("") as f:
            tg.create_task(bar(f))  # error: 31, lineno-1, lineno-2, "f", "create_task"

            # start[_soon] does not exist in asyncio, but gets errors anyway
            await tg.start(bar, f)  # error: 32, lineno-4, lineno-5, "f", "start"
            tg.start_soon(bar, f)  # error: 31, lineno-5, lineno-6, "f", "start_soon"
