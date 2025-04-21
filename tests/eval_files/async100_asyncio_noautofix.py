# TRIO_NO_ERROR
# ANYIO_NO_ERROR
# BASE_LIBRARY asyncio

# We remove the last timeout, but don't re-evaluate the whole with statement,
# so the test still raises an error.
# NOAUTOFIX

# asyncio.timeout[_at] added in py3.11
# mypy: disable-error-code=attr-defined

import asyncio


async def multi_withitem():
    async with asyncio.timeout(
        10
    ), asyncio.timeout_at(  # error: 7, "asyncio", "timeout_at"
        10
    ):
        ...
