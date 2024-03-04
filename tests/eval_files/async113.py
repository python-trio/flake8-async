# mypy: disable-error-code="arg-type,attr-defined"
# NOASYNCIO - with two "base libraries" this file will raise errors even if substituting one of them
from contextlib import asynccontextmanager

import anyio
import trio

# NOANYIO - this file checks both libraries


@asynccontextmanager
async def foo():
    with trio.open_nursery() as bar:
        bar.start_soon(trio.run_process)  # ASYNC113: 8
    async with trio.open_nursery() as bar:
        bar.start_soon(trio.run_process)  # ASYNC113: 8

    async with anyio.create_task_group() as bar_tg:
        bar_tg.start_soon(anyio.run_process)  # ASYNC113: 8

    boo: trio.Nursery = ...  # type: ignore
    boo.start_soon(trio.run_process)  # ASYNC113: 4

    boo_anyio: anyio.TaskGroup = ...  # type: ignore
    boo_anyio.start_soon(anyio.run_process)  # ASYNC113: 4

    yield
