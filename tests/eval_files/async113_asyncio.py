# BASE_LIBRARY asyncio
# ARG --startable-in-context-manager=bar
# TRIO_NO_ERROR
# ANYIO_NO_ERROR

from contextlib import asynccontextmanager
import asyncio


async def bar(): ...


@asynccontextmanager
async def my_cm():
    async with asyncio.TaskGroup() as tg:  # type: ignore[attr-defined]
        tg.create_task(bar)  # ASYNC113: 8
        yield
