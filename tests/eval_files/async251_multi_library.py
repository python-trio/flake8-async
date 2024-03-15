# BASE_LIBRARY trio
# NOASYNCIO # tests asyncio without replacing for it
import trio
import time
import asyncio


async def foo():
    time.sleep(5)  # ASYNC251: 4, "[trio/asyncio]"
