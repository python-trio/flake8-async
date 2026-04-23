# 3rd-party context managers with internal cancel scopes / nurseries /
# task groups. `yield`ing inside any of them breaks exception handling.
#
# Package names like `trio_websocket` / `qtrio` survive the test framework's
# `trio` -> `anyio` / `asyncio` library substitution because that substitution
# only matches at word boundaries.
from contextlib import asynccontextmanager

import anyio.from_thread
import apscheduler
import asgi_lifespan
import mcp.client.sse
import mcp.client.streamable_http
import qtrio
import trio_asyncio
import trio_parallel
import trio_util
import trio_websocket


# trio_websocket
async def foo_open_websocket():
    async with trio_websocket.open_websocket("h", 80, "/", use_ssl=False) as _:
        yield 1  # error: 8


async def foo_open_websocket_url():
    async with trio_websocket.open_websocket_url("ws://x") as _:
        yield 1  # error: 8


async def foo_serve_websocket():
    async with trio_websocket.serve_websocket(
        lambda *_: None, "h", 80, ssl_context=None
    ) as _:
        yield 1  # error: 8


@asynccontextmanager
async def foo_trio_websocket_safe():
    async with trio_websocket.open_websocket_url("ws://x") as _:
        yield 1  # safe


# trio_asyncio
async def foo_open_loop():
    async with trio_asyncio.open_loop() as _:
        yield 1  # error: 8


# trio_parallel
async def foo_open_worker_context():
    async with trio_parallel.open_worker_context() as _:
        yield 1  # error: 8


# trio_util
async def foo_move_on_when():
    async with trio_util.move_on_when(lambda: None) as _:
        yield 1  # error: 8


async def foo_run_and_cancelling():
    async with trio_util.run_and_cancelling(lambda: None) as _:
        yield 1  # error: 8


# qtrio
async def foo_open_emissions_nursery():
    async with qtrio.open_emissions_nursery() as _:
        yield 1  # error: 8


async def foo_enter_emissions_channel():
    async with qtrio.enter_emissions_channel(signals=()) as _:
        yield 1  # error: 8


# asgi_lifespan
async def foo_lifespan_manager():
    async with asgi_lifespan.LifespanManager(None) as _:
        yield 1  # error: 8


@asynccontextmanager
async def foo_lifespan_manager_safe():
    async with asgi_lifespan.LifespanManager(None) as _:
        yield 1  # safe


# apscheduler v4
async def foo_async_scheduler():
    async with apscheduler.AsyncScheduler() as _:
        yield 1  # error: 8


# anyio.from_thread
async def foo_blocking_portal():
    with anyio.from_thread.BlockingPortal() as _:
        yield 1  # error: 8


async def foo_start_blocking_portal():
    with anyio.from_thread.start_blocking_portal() as _:
        yield 1  # error: 8


# MCP SDK
async def foo_streamablehttp_client():
    async with mcp.client.streamable_http.streamablehttp_client("http://x") as _:
        yield 1  # error: 8


async def foo_sse_client():
    async with mcp.client.sse.sse_client("http://x") as _:
        yield 1  # error: 8
