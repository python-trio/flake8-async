# TRIO_NO_ERROR
# ANYIO_NO_ERROR
# BASE_LIBRARY asyncio

# asyncio.timeout[_at] added in py3.11
# mypy: disable-error-code=attr-defined
# AUTOFIX

import asyncio


async def foo():
    # error: 9, "asyncio", "timeout_at"
    ...
    # error: 9, "asyncio", "timeout"
    ...


# this is technically only a problem with asyncio, since timeout primitives in trio/anyio
# are sync cm's
async def multi_withitem():
    with open("foo"):  # error: 9, "asyncio", "timeout"
        ...
    with open("foo"):  # error: 22, "asyncio", "timeout"
        ...
    # retain explicit trailing comma (?)
    with (
        open("foo"),
        open("bar"),  # error: 8, "asyncio", "timeout"
    ):
        ...
