# AUTOFIX
# BASE_LIBRARY anyio
# NOTRIO  # trio.create_task_group doesn't exist
# ASYNCIO_NO_ERROR
import anyio


async def bar() -> None: ...


async def anyio_cancelscope():
    with anyio.CancelScope():  # error: 9, "anyio", "CancelScope"
        ...


# see async100_trio for more comprehensive tests
async def nursery_no_cancel_point():
    with anyio.CancelScope():  # error: 9, "anyio", "CancelScope"
        async with anyio.create_task_group():
            ...


async def nursery_with_start_soon():
    with anyio.CancelScope():
        async with anyio.create_task_group() as tg:
            tg.start_soon(bar)
