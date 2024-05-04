# ARG --enable=ASYNC100,ASYNC912
# BASE_LIBRARY asyncio
# ANYIO_NO_ERROR
# TRIO_NO_ERROR

# ASYNC100 supports autofix, but ASYNC912 doesn't, so we must run with NOAUTOFIX
# NOAUTOFIX

# timeout[_at] added in py3.11
# mypy: disable-error-code=attr-defined

import asyncio


def bar() -> bool:
    return False


async def foo():
    async with asyncio.timeout(10):  # ASYNC100: 15, "asyncio", "timeout"
        ...
    async with asyncio.timeout_at(10):  # ASYNC100: 15, "asyncio", "timeout_at"
        ...

    async with asyncio.timeout(10):
        await foo()
    async with asyncio.timeout_at(10):
        await foo()

    async with asyncio.timeout_at(10):  # ASYNC912: 4
        if bar():
            await foo()
    async with asyncio.timeout(10):  # ASYNC912: 4
        if bar():
            await foo()
