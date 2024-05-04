# TRIO_NO_ERROR
# ANYIO_NO_ERROR
# BASE_LIBRARY asyncio

# mypy: disable-error-code=attr-defined
# AUTOFIX

import asyncio
import asyncio.timeouts


async def foo():
    # py>=3.11 re-exports these in the main asyncio namespace
    # error: 9, "asyncio", "timeout_at"
    ...
    # error: 9, "asyncio", "timeout"
    ...

    # TODO
    with asyncio.timeouts.timeout_at(10):
        ...
    with asyncio.timeouts.timeout_at(10):
        ...
    with asyncio.timeouts.timeout(10):
        ...
