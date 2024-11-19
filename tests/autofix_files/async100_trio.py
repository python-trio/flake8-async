# AUTOFIX
# ASYNCIO_NO_ERROR # asyncio.open_nursery doesn't exist
# ANYIO_NO_ERROR # anyio.open_nursery doesn't exist
import trio


async def nursery_no_cancel_point():
    with trio.CancelScope():  # should error, but reverted PR
        async with trio.open_nursery():
            ...
