# ARG --enable=ASYNC100,ASYNC912
# BASE_LIBRARY asyncio
# ANYIO_NO_ERROR
# TRIO_NO_ERROR

# ASYNC100 supports autofix, but ASYNC912 doesn't, so we must run with NOAUTOFIX
# NOAUTOFIX

# asyncio.timeout[_at] added in py3.11
# mypy: disable-error-code=attr-defined

import asyncio

from typing import Any


def bar() -> Any:
    return False


async def foo():
    # async100
    async with asyncio.timeout(10):  # ASYNC100: 15, "asyncio", "timeout"
        ...
    async with asyncio.timeout_at(10):  # ASYNC100: 15, "asyncio", "timeout_at"
        ...

    # no errors
    async with asyncio.timeout(10):
        await foo()
    async with asyncio.timeout_at(10):
        await foo()

    # async912
    async with asyncio.timeout_at(10):  # ASYNC912: 15
        if bar():
            await foo()
    async with asyncio.timeout(10):  # ASYNC912: 15
        if bar():
            await foo()

    # multiple withitems
    async with asyncio.timeout(10), bar():
        ...
    async with bar(), asyncio.timeout(10):  # ASYNC912: 22
        if bar():
            await foo()

    # double check that helper methods used by visitor don't trigger erroneously
    timeouts: Any
    timeout_at: Any
    async with asyncio.timeout_at.timeouts(10):
        ...
    async with timeouts.asyncio.timeout_at(10):
        ...
    async with timeouts.timeout_at.asyncio(10):
        ...
    async with timeout_at.asyncio.timeouts(10):
        ...
    async with timeout_at.timeouts.asyncio(10):
        ...
    async with foo.timeout(10):
        ...
    async with asyncio.timeouts(10):
        ...
