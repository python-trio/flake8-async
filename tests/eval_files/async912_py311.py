# ASYNC912 can't be tested with the other 91x rules since there's no universal
# cancelscope name across trio/asyncio/anyio - so we need ASYNCIO_NO_ERROR


# ASYNCIO_NO_ERROR
async def foo(): ...


async def check_async912():
    with trio.move_on_after(30):  # ASYNC912: 9
        try:
            await foo()
        except* ValueError:
            # Missing checkpoint
            ...
    await foo()
