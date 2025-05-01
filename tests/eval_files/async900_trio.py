import trio

# different error message & no as_safe_channel
# NOANYIO
# NOASYNCIO


async def foo1():  # ASYNC900: 0, 'trio.as_safe_channel, contextlib.asynccontextmanager, pytest.fixture'
    yield
    yield


@trio.as_safe_channel
async def foo():
    yield
