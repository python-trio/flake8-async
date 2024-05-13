# BASE_LIBRARY asyncio
# TRIO_NO_ERROR
# ANYIO_NO_ERROR
# TaskGroup and timeout[_at] was added in 3.11, we run type checking with 3.9
# mypy: disable-error-code=attr-defined
import contextlib
import contextlib as bla
from contextlib import asynccontextmanager, contextmanager, contextmanager as blahabla

import asyncio
import pytest


async def test_async_with():
    async with asyncio.TaskGroup() as _:
        yield 1  # error: 8


async def test_timeout():
    async with asyncio.timeout() as _:
        yield 1  # error: 8


async def test_timeout_at():
    async with asyncio.timeout_at() as _:
        yield 1  # error: 8


async def test_nested_method():
    async with asyncio.TaskGroup():
        yield 1  # error: 8

        def foo6():
            yield 1  # safe


# TaskGroup is an async cm, but the visitor does not care about that
def test_with():
    with asyncio.TaskGroup() as _:
        yield 1  # error: 8


@contextmanager
def safe_1():
    with asyncio.TaskGroup() as _:
        yield 1  # safe


@asynccontextmanager
async def safe_2():
    async with asyncio.TaskGroup() as _:
        yield 1  # safe


@contextlib.asynccontextmanager
async def safe_3():
    async with asyncio.TaskGroup() as _:
        yield 1  # safe


@bla.contextmanager
def safe_4():
    with asyncio.TaskGroup() as _:
        yield 1  # safe


@blahabla
def test_unrelated_decorator():
    with asyncio.TaskGroup() as _:
        yield 1  # error: 8


@pytest.fixture()
def foo_false_alarm():
    with asyncio.TaskGroup() as _:
        yield 1


@pytest.fixture
def foo_false_alarm_2():
    with asyncio.TaskGroup() as _:
        yield 1
