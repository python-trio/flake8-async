import contextlib

from contextlib import asynccontextmanager


async def unsafe_yield():
    with open(""):
        yield  # error: 8


async def async_with():
    async with unsafe_yield():
        yield  # error: 8


async def warn_on_yeach_yield():
    with open(""):
        yield  # error: 8
        yield  # error: 8
    with open(""):
        yield  # error: 8
        yield  # error: 8


async def yield_not_in_contextmanager():
    yield
    with open(""):
        ...
    yield


async def yield_in_nested_function():
    with open(""):

        def foo():
            yield


async def yield_in_nested_async_function():
    with open(""):

        async def foo():
            yield


async def yield_after_nested_async_function():
    with open(""):

        async def foo():
            yield

        yield  # error: 8


@asynccontextmanager
async def safe_in_contextmanager():
    with open(""):
        yield


@contextlib.asynccontextmanager
async def safe_in_contextmanager2():
    with open(""):
        yield
