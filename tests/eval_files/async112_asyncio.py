# main tests in async112.py
# this only tests asyncio.TaskGroup in particular
# BASE_LIBRARY asyncio
# ANYIO_NO_ERROR
# TRIO_NO_ERROR
# TaskGroup introduced in 3.11, we run typechecks with 3.9
# mypy: disable-error-code=attr-defined

import asyncio


async def bar(*args): ...


async def foo():
    async with asyncio.TaskGroup() as tg:  # error: 15, "tg", "task group"
        tg.create_task(bar())

    async with asyncio.TaskGroup() as tg:
        tg.create_task(bar(tg))

    # will not trigger on start / start_soon
    async with asyncio.TaskGroup() as tg:
        tg.start(bar())
