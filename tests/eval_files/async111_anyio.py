# main tests in async111.py
# this only tests anyio.create_task_group in particular
# BASE_LIBRARY anyio
# ASYNCIO_NO_ERROR
# TRIO_NO_ERROR


import anyio


async def bar(*args): ...


async def foo():
    async with anyio.create_task_group() as tg:
        with open("") as f:
            await tg.start(bar, f)  # error: 32, lineno-1, lineno-2, "f", "start"
            tg.start_soon(bar, f)  # error: 31, lineno-2, lineno-3, "f", "start_soon"

            # create_task does not exist in anyio, but gets errors anyway
            tg.create_task(bar(f))  # type: ignore[attr-defined] # error: 31, lineno-5, lineno-6, "f", "create_task"
