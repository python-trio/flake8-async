# TRIO_NO_ERROR
# ANYIO_NO_ERROR
# BASE_LIBRARY asyncio

# asyncio.timeout[_at] added in py3.11
# mypy: disable-error-code=attr-defined
# AUTOFIX

import asyncio


async def foo():
    with asyncio.timeout_at(10):  # error: 9, "asyncio", "timeout_at"
        ...
    with asyncio.timeout(10):  # error: 9, "asyncio", "timeout"
        ...


# this is technically only a problem with asyncio, since timeout primitives in trio/anyio
# are sync cm's
async def multi_withitem():
    with asyncio.timeout(10), open("foo"):  # error: 9, "asyncio", "timeout"
        ...
    with open("foo"), asyncio.timeout(10):  # error: 22, "asyncio", "timeout"
        ...
    # retain explicit trailing comma (?)
    with (
        open("foo"),
        open("bar"),
        asyncio.timeout(10),  # error: 8, "asyncio", "timeout"
    ):
        ...
