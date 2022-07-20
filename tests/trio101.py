import contextlib
import contextlib as bla
from contextlib import asynccontextmanager, contextmanager

import trio


def foo0():
    with trio.open_nursery() as _:
        yield 1  # error


async def foo1():
    async with trio.open_nursery() as _:
        yield 1  # error


@contextmanager
def foo2():
    with trio.open_nursery() as _:
        yield 1  # safe


async def foo3():
    async with trio.CancelScope() as _:
        await trio.sleep(1)  # so trio100 doesn't complain
        yield 1  # error


@asynccontextmanager
async def foo4():
    async with trio.open_nursery() as _:
        yield 1  # safe


async def foo5():
    async with trio.open_nursery():
        yield 1  # error

        def foo6():
            yield 1  # safe


@contextlib.asynccontextmanager
async def foo7():
    async with trio.open_nursery() as _:
        yield 1  # safe


@bla.contextmanager
def foo8():
    with trio.open_nursery() as _:
        yield 1  # safe
