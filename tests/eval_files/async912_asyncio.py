# BASE_LIBRARY asyncio
# ANYIO_NO_ERROR
# TRIO_NO_ERROR

# timeout[_at] added in py3.11
# mypy: disable-error-code=attr-defined

import asyncio


async def foo():
    async with asyncio.timeout(10):  # error: 4
        ...
    async with asyncio.timeout(10):
        await foo()
    async with asyncio.timeout_at(10):  # error: 4
        ...
    async with asyncio.timeout_at(10):
        await foo()
