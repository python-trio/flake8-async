# TRIO_NO_ERROR
# ANYIO_NO_ERROR
# BASE_LIBRARY asyncio

# timeout[_at] re-exported in the main asyncio namespace in py3.11
# mypy: disable-error-code=attr-defined
# AUTOFIX

import asyncio
import asyncio.timeouts


async def foo():
    # error: 9, "asyncio", "timeout_at"
    ...
    # error: 9, "asyncio", "timeout"
    ...

    # error: 9, "asyncio.timeouts", "timeout_at"
    ...
    # error: 9, "asyncio.timeouts", "timeout"
    ...
