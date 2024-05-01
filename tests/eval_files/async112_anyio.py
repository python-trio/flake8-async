# main tests in async112.py
# this only tests anyio.create_task_group in particular
# BASE_LIBRARY anyio
# ASYNCIO_NO_ERROR
# TRIO_NO_ERROR

import anyio


async def bar(*args): ...


async def foo():
    async with anyio.create_task_group() as tg:  # error: 15, "tg"
        await tg.start_soon(bar())

    async with anyio.create_task_group() as tg:
        await tg.start(bar(tg))

    async with anyio.create_task_group() as tg:  # error: 15, "tg"
        tg.start_soon(bar())

    async with anyio.create_task_group() as tg:
        tg.start_soon(bar(tg))

    # will not trigger on create_task
    async with anyio.create_task_group() as tg:
        tg.create_task(bar())  # type: ignore[attr-defined]
