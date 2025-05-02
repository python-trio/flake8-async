# mypy: disable-error-code="arg-type,attr-defined"
# ARG --startable-in-context-manager=my_startable
from __future__ import annotations
from contextlib import asynccontextmanager

import anyio
import trio

# set base library to anyio, so we can replace anyio->asyncio and get correct errors
# BASE_LIBRARY trio
# ASYNCIO_NO_ERROR

# This file tests basic errors, and async113_trio_anyio checks errors not compatible
# with asyncio


async def my_startable(task_status: trio.TaskStatus[object] = trio.TASK_STATUS_IGNORED):
    task_status.started()
    await trio.lowlevel.checkpoint()


@asynccontextmanager
async def foo():
    # we don't check for `async with`
    with trio.open_nursery() as bar:  # type: ignore[attr-defined]
        bar.start_soon(my_startable)  # ASYNC113: 8
        yield


@asynccontextmanager
async def foo2():
    async with trio.open_nursery() as bar:
        bar.start_soon(my_startable)  # ASYNC113: 8
        yield


@asynccontextmanager
async def foo3():
    boo: trio.Nursery = ...  # type: ignore
    boo.start_soon(my_startable)  # ASYNC113: 4

    # silence type errors
    serve = run_process = serve_listeners = serve_tcp = serve_ssl_over_tcp = (
        my_startable
    )

    # we also trigger if they're a standalone name, assuming that this is
    # a wrapper. (or they've ignored the error from doing `from trio import run_process`)
    boo.start_soon(serve)  # error: 4
    boo.start_soon(run_process)  # error: 4
    boo.start_soon(serve_listeners)  # error: 4
    boo.start_soon(serve_tcp)  # error: 4
    boo.start_soon(serve_ssl_over_tcp)  # error: 4

    yield


# we don't type-track [trio/anyio].DTLSEndpoint, so we trigger
# on *.serve
@asynccontextmanager
async def foo_serve(nursey: trio.Nursery, thing: object):
    nursey.start_soon(thing.serve)  # ASYNC113: 4


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
            bar.start_soon(my_startable)

        yield


@asynccontextmanager
async def false_alarm():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(my_startable)
    yield


@asynccontextmanager
async def should_error():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(my_startable)  # ASYNC113: 8
        # overrides the nursery variable
        async with trio.open_nursery() as nursery:
            nursery.start_soon(my_startable)
        yield


@asynccontextmanager
async def foo_sync_with_closed():
    # we don't check for `async with`
    with trio.open_nursery() as bar:  # type: ignore[attr-defined]
        bar.start_soon(my_startable)
    yield


# fixed by entirely skipping nurseries without yields in them
class FalseAlarm:
    async def __aenter__(self):
        with trio.open_nursery() as nursery:
            nursery.start_soon(my_startable)


@asynccontextmanager
async def yield_before_start_soon():
    with trio.open_nursery() as bar:
        yield
        bar.start_soon(my_startable)


# This was broken when visit_AsyncWith manually visited subnodes due to not
# letting TypeTrackerVisitor interject.
@asynccontextmanager
async def nested():
    with trio.open_nursery() as foo:
        with trio.open_nursery() as bar:
            bar.start_soon(my_startable)  # error: 12
            yield
