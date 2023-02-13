# mypy: disable-error-code="arg-type,attr-defined"
from contextlib import asynccontextmanager

import anyio
import trio

# NOANYIO - requires no substitution check


@asynccontextmanager
async def foo():
    with trio.open_nursery() as bar:
        bar.start_soon(trio.run_process)  # TRIO113: 8
    async with trio.open_nursery() as bar:
        bar.start_soon(trio.run_process)  # TRIO113: 8

    async with anyio.create_task_group() as bar_tg:
        bar_tg.start_soon(anyio.run_process)  # TRIO113: 8

    boo: trio.Nursery = ...  # type: ignore
    boo.start_soon(trio.run_process)  # TRIO113: 4

    boo_anyio: anyio.TaskGroup = ...  # type: ignore
    boo_anyio.start_soon(anyio.run_process)  # TRIO113: 4

    yield
