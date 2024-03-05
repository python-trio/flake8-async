# mypy: disable-error-code="arg-type"
from contextlib import asynccontextmanager

import anyio


@asynccontextmanager
async def foo():
    # create_task_group only exists in anyio
    async with anyio.create_task_group() as bar_tg:
        bar_tg.start_soon(anyio.run_process)  # ASYNC113: 8
    yield
