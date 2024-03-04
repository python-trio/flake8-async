# TRIO_NO_ERROR
# ANYIO_NO_ERROR
# BASE_LIBRARY asyncio
# ASYNCIO_NO_ERROR # TODO

import asyncio
import asyncio.timeouts


async def foo():
    # py>=3.11 re-exports these in the main asyncio namespace
    with asyncio.timeout_at(10):  # type: ignore[attr-defined]
        ...
    with asyncio.timeout_at(10):  # type: ignore[attr-defined]
        ...
    with asyncio.timeout(10):  # type: ignore[attr-defined]
        ...
    with asyncio.timeouts.timeout_at(10):
        ...
    with asyncio.timeouts.timeout_at(10):
        ...
    with asyncio.timeouts.timeout(10):
        ...
