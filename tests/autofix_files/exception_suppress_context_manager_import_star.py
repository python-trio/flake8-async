# ARG --enable=ASYNC910
# see exception_suppress_context_manager.py for main testing

# AUTOFIX
# ASYNCIO_NO_AUTOFIX

from contextlib import *
import trio


async def foo():  # ASYNC910: 0, "exit", Statement('function definition', lineno)
    with suppress():
        await foo()
    await trio.lowlevel.checkpoint()
