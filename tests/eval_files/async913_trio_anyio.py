# ARG --enable=ASYNC913
# AUTOFIX
# ASYNCIO_NO_ERROR

import trio


async def nursery_no_cancel_point():
    while True:  # ASYNC913: 4
        async with trio.open_nursery():
            pass
