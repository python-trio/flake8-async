# TRIO_NO_ERROR
# ANYIO_NO_ERROR
# BASE_LIBRARY asyncio

# timeout[_at] re-exported in the main asyncio namespace in py3.11
# mypy: disable-error-code=attr-defined
# AUTOFIX

import asyncio
import asyncio.timeouts


async def foo():
    with asyncio.timeout_at(10):  # error: 9, "asyncio", "timeout_at"
        ...
    with asyncio.timeout(10):  # error: 9, "asyncio", "timeout"
        ...

    with asyncio.timeouts.timeout_at(10):  # error: 9, "asyncio.timeouts", "timeout_at"
        ...
    with asyncio.timeouts.timeout(10):  # error: 9, "asyncio.timeouts", "timeout"
        ...
