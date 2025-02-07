# ARG --no-checkpoint-warning-decorator=no_checkpoint_warning_decorator
# ARG --transform-async-generator-decorators=transform_async_gen_decorator
import contextlib

from contextlib import asynccontextmanager


async def unsafe_yield():
    with open(""):
        yield  # error: 8


async def async_with():
    async with unsafe_yield():
        yield  # error: 8


async def warn_on_each_yield():
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


def no_checkpoint_warning_decorator(_: object): ...


def transform_async_gen_decorator(_: object): ...


@no_checkpoint_warning_decorator
async def no_checkpoint_warning_deco_fun():
    with open(""):
        yield  # error: 8


@transform_async_gen_decorator
async def transfor_async_gen_deco_fun():
    with open(""):
        yield  # safe
