# BASE_LIBRARY anyio
# ASYNCIO_NO_ERROR

import anyio


async def foo():
    async with anyio.create_task_group():
        yield 1  # error: 8
