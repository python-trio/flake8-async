from contextlib import asynccontextmanager, contextmanager

import trio


def foo0():
    with trio.open_nursery() as _:
        yield 1


async def foo1():
    async with trio.open_nursery() as _:
        yield 1


@contextmanager
def foo2():
    with trio.open_nursery() as _:
        yield 1


@asynccontextmanager
async def foo3():
    async with trio.open_nursery() as _:
        yield 1
