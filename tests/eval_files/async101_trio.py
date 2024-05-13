# ASYNCIO_NO_ERROR
# ANYIO_NO_ERROR

from contextlib import asynccontextmanager

import trio


async def foo_open_nursery():
    async with trio.open_nursery() as _:
        yield 1  # error: 8


@asynccontextmanager
async def foo_open_nursery_contextmanager():
    async with trio.open_nursery() as _:
        yield 1  # safe
