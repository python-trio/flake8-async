# ARG --enable=ASYNC100,ASYNC912
# BASE_LIBRARY asyncio
# ANYIO_NO_ERROR
# TRIO_NO_ERROR

# ASYNC100 supports autofix, but ASYNC912 doesn't, so we must run with NOAUTOFIX
# NOAUTOFIX

# timeout[_at] re-exported in the main asyncio namespace in py3.11
# mypy: disable-error-code=attr-defined

import asyncio


def bar() -> bool:
    return False


async def foo():
    # async100
    async with asyncio.timeout(10):  # ASYNC100: 15, "asyncio", "timeout"
        ...
    async with asyncio.timeout_at(10):  # ASYNC100: 15, "asyncio", "timeout_at"
        ...
    async with asyncio.timeouts.timeout(
        10
    ):  # ASYNC100: 15, "asyncio.timeouts", "timeout"
        ...
    async with asyncio.timeouts.timeout_at(
        10
    ):  # ASYNC100: 15, "asyncio.timeouts", "timeout_at"
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

    async with asyncio.timeouts.timeout(10):  # ASYNC912: 15
        if bar():
            await foo()
    async with asyncio.timeouts.timeout_at(10):  # ASYNC912: 15
        if bar():
            await foo()
