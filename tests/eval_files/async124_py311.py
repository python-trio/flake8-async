from contextlib import asynccontextmanager


@asynccontextmanager
async def foo():
    try:
        yield
    except* Exception:
        ...


@asynccontextmanager
async def bar():
    try:
        ...
    except* Exception:
        yield  # error: 8
