# AUTOFIX
# ASYNCIO_NO_ERROR # asyncio.open_nursery doesn't exist
# NOANYIO # anyio.open_nursery doesn't exist
import trio


async def nursery_no_cancel_point():
    with trio.CancelScope():  # error: 9, "trio", "CancelScope"
        async with trio.open_nursery():
            ...


# but it is a cancel point if the nursery contains a call to start_soon()


async def nursery_start_soon():
    with trio.CancelScope():
        async with trio.open_nursery() as n:
            n.start_soon(trio.sleep, 0)


async def nursery_start_soon_misnested():
    async with trio.open_nursery() as n:
        with trio.CancelScope():  # error: 13, "trio", "CancelScope"
            n.start_soon(trio.sleep, 0)


async def nested_scope():
    with trio.CancelScope():
        with trio.CancelScope():
            async with trio.open_nursery() as n:
                n.start_soon(trio.sleep, 0)


async def nested_nursery():
    with trio.CancelScope():
        async with trio.open_nursery() as n:
            async with trio.open_nursery() as n2:
                n2.start_soon(trio.sleep, 0)


async def nested_function_call():

    with trio.CancelScope():  # error: 9, "trio", "CancelScope"
        async with trio.open_nursery() as n:

            def foo():
                n.start_soon(trio.sleep, 0)

            # a false alarm in case we call foo()... but we can't check if they do
            foo()


# insert cancel point on nursery exit, not at the start_soon call
async def cancel_point_on_nursery_exit():
    with trio.CancelScope():
        async with trio.open_nursery() as n:
            with trio.CancelScope():  # error: 17, "trio", "CancelScope"
                n.start_soon(trio.sleep, 0)


# async100 does not consider *redundant* cancel scopes
async def redundant_cancel_scope():
    with trio.CancelScope():
        with trio.CancelScope():
            await trio.lowlevel.checkpoint()


# but if it did then none of these scopes should be marked redundant
# The inner checks task startup, the outer checks task exit
async def nursery_exit_blocks_with_start():
    with trio.CancelScope():
        async with trio.open_nursery() as n:
            with trio.CancelScope():
                await n.start(trio.sleep, 0)
