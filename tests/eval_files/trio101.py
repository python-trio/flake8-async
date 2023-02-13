# type: ignore
import contextlib
import contextlib as bla
from contextlib import asynccontextmanager, contextmanager, contextmanager as blahabla

import trio


def foo0():
    with trio.open_nursery() as _:
        yield 1  # error: 8


async def foo1():
    async with trio.open_nursery() as _:
        yield 1  # error: 8


@contextmanager
def foo2():
    with trio.open_nursery() as _:
        yield 1  # safe


async def foo3():
    async with trio.CancelScope() as _:
        yield 1  # error: 8


@asynccontextmanager
async def foo4():
    async with trio.open_nursery() as _:
        yield 1  # safe


async def foo5():
    async with trio.open_nursery():
        yield 1  # error: 8

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


@blahabla
def foo9():
    with trio.open_nursery() as _:
        yield 1  # error: 8
