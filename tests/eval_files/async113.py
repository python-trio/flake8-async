# mypy: disable-error-code="arg-type,attr-defined"
# ARG --startable-in-context-manager=my_startable
from __future__ import annotations
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
    # false alarm - anyio.run_process is not startable
    # (nor is asyncio.run_process)
    boo_anyio.start_soon(anyio.run_process)  # ASYNC113: 4

    yield


async def my_startable(task_status: trio.TaskStatus[object] = trio.TASK_STATUS_IGNORED):
    task_status.started()
    await trio.lowlevel.checkpoint()


# name of variable being [xxx.]nursery triggers it
class MyCm_named_variable:
    def __init__(self):
        self.nursery_manager = trio.open_nursery()
        self.nursery = None

    async def __aenter__(self):
        self.nursery = await self.nursery_manager.__aenter__()
        self.nursery.start_soon(my_startable)  # ASYNC113: 8

    async def __aexit__(self, *args):
        assert self.nursery is not None
        await self.nursery_manager.__aexit__(*args)


# call chain is not tracked
# trio.open_nursery -> NurseryManager
# NurseryManager.__aenter__ -> nursery
class MyCm_calls:
    async def __aenter__(self):
        self.nursery_manager = trio.open_nursery()
        self.moo = None
        self.moo = await self.nursery_manager.__aenter__()
        self.moo.start_soon(my_startable)

    async def __aexit__(self, *args):
        assert self.moo is not None
        await self.nursery_manager.__aexit__(*args)


# types of class variables are not tracked across functions
class MyCm_typehint_class_variable:
    def __init__(self):
        self.nursery_manager = trio.open_nursery()
        self.moo: trio.Nursery = None  # type: ignore

    async def __aenter__(self):
        self.moo = await self.nursery_manager.__aenter__()
        self.moo.start_soon(my_startable)

    async def __aexit__(self, *args):
        assert self.moo is not None
        await self.nursery_manager.__aexit__(*args)


# type hint with __or__ is not picked up
class MyCm_typehint:
    async def __aenter__(self):
        self.nursery_manager = trio.open_nursery()
        self.moo: trio.Nursery | None = None
        self.moo = await self.nursery_manager.__aenter__()
        self.moo.start_soon(my_startable)

    async def __aexit__(self, *args):
        assert self.moo is not None
        await self.nursery_manager.__aexit__(*args)


# only if the type hint is exactly trio.Nursery
class MyCm_typehint_explicit:
    async def __aenter__(self):
        self.nursery_manager = trio.open_nursery()
        self.moo: trio.Nursery = None  # type: ignore
        self.moo = await self.nursery_manager.__aenter__()
        self.moo.start_soon(my_startable)  # ASYNC113: 8

    async def __aexit__(self, *args):
        assert self.moo is not None
        await self.nursery_manager.__aexit__(*args)


@asynccontextmanager
async def foo_nested_sync_def():
    with trio.open_nursery() as bar:

        def non_async_func():
            bar.start_soon(trio.run_process)

        yield
