# mypy: disable-error-code="arg-type,attr-defined"
from contextlib import asynccontextmanager

import anyio
import trio

# set base library to anyio, so we can replace anyio->asyncio and get correct errors
# BASE_LIBRARY anyio

# NOTRIO - replacing anyio->trio would give mismatching errors.
# This file tests basic trio errors, and async113_trio checks trio-specific errors


@asynccontextmanager
async def foo():
    with trio.open_nursery() as bar:
        bar.start_soon(trio.run_process)  # ASYNC113: 8
    async with trio.open_nursery() as bar:
        bar.start_soon(trio.run_process)  # ASYNC113: 8

    boo: trio.Nursery = ...  # type: ignore
    boo.start_soon(trio.run_process)  # ASYNC113: 4

    boo_anyio: anyio.TaskGroup = ...  # type: ignore
    boo_anyio.start_soon(anyio.run_process)  # ASYNC113: 4

    yield
