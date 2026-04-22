# 3rd-party context managers with internal cancel scopes / nurseries.
# These names don't contain "trio" / "anyio" as substrings (or only contain
# them in a position that survives the test framework's library substitution),
# so this file is checked under all three libraries.
from contextlib import asynccontextmanager

import anyio.from_thread
import apscheduler
import asgi_lifespan
import mcp.client.sse
import mcp.client.streamable_http


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
