# ANYIO_NO_ERROR
# ASYNCIO_NO_ERROR
# These trio-named third-party packages also open internal nurseries / cancel
# scopes. The test framework substitutes "trio" -> "anyio" / "asyncio" in eval
# files, which mangles the package names; the markers above suppress expected
# errors for the substituted variants (the linter still runs to verify it
# doesn't crash).
from contextlib import asynccontextmanager

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
