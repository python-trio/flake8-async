# type: ignore
# ASYNCIO_NO_ERROR # no asyncio.lowlevel.checkpoint()
import time

import trio
from trio import sleep


async def afoo():
    # only error on exactly one argument, that is 0
    await trio.sleep(0)  # error: 10, "trio"
    await trio.sleep(1)
    await trio.sleep(0, 1)
    await trio.sleep(...)
    await trio.sleep()

    # don't require it being await'ed
    trio.sleep(0)  # error: 4, "trio"
    trio.sleep(1)

    # don't error on other sleeps
    time.sleep(0)
    sleep(0)

    # in trio it's called 'seconds', in anyio it's 'delay', but
    # we don't care about the kwarg name. #382
    await trio.sleep(seconds=0)  # error: 10, "trio"
    await trio.sleep(delay=0)  # error: 10, "trio"
    await trio.sleep(anything=0)  # error: 10, "trio"

    await trio.sleep(seconds=1)

    await trio.sleep()

    # we don't care to suppress this
    await trio.sleep(0, seconds=1)  # error: 10, "trio"


# don't require being inside a function
trio.sleep(0)  # error: 0, "trio"


def foo():
    # can be inside a sync function, and inside other calls
    # (though yes this is invalid code)
    trio.run(trio.sleep(0))  # error: 13, "trio"
