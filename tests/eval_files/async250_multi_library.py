# BASE_LIBRARY trio
# NOASYNCIO # tests asyncio without replacing for it
import trio
import asyncio


async def foo():
    k = input()  # ASYNC250: 8, 'trio.to_thread.run_sync/asyncio.loop.run_in_executor'
    input("$")  # ASYNC250: 4,  'trio.to_thread.run_sync/asyncio.loop.run_in_executor'
