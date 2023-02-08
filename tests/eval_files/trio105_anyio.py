# NOTRIO
import anyio


# nurseries don't exist in anyio, so don't error on it.
async def foo():
    nursery = anyio.open_nursery()
    await nursery.start()
    await nursery.start_foo()

    nursery.start()  # should not be triggered with anyio
    None.start()
    nursery.start_soon()
    nursery.start_foo()