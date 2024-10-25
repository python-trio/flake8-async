from contextlib import asynccontextmanager


@asynccontextmanager
async def foo():
    try:
        # TODO: should it error if there is no finally?
        yield
    except:
        ...


@asynccontextmanager
async def foo2():
    try:
        ...
    except:
        yield  # error: 8
